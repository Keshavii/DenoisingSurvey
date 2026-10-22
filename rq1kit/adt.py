"""T-CE and R-CE (ADT, Wang et al., WSDM 2021) on the kit's backbones: Part C adapter (code-change class 4).

Only the loss differs from rq1kit.backbone; data, backbone, negative sampling, regularisation, model selection
(clean-validation NDCG@20), early stopping and the top-K export are the kit's, so every Part C method is compared
like for like. The two losses follow the authors' DenoisingRec code (T_CE/loss.py, R_CE/loss.py, T_CE/main.py):

  T-CE  per-sample BCE over the positives and their sampled negatives; samples are ranked by loss * label
        (negatives score 0) and the drop_rate share with the largest loss is dropped. drop_rate rises linearly
        from 0 to drop_rate ** exponent over the first num_gradual iterations (drop_rate_schedule in main.py).
  R-CE  per-sample BCE weighted by sigmoid(pred) ** alpha for positives and (1 - sigmoid(pred)) ** alpha for
        negatives, weights detached.

Scaling matches the kit's plain BCE exactly (sum of the positive and negative terms per pair), so T-CE with
drop_rate 0 and R-CE with alpha 0 reproduce Plain-BCE step for step (checked by --selftest).

  python -m rq1kit.adt --method tce --drop_rate 0.2 --num_gradual 30000 --data data/yelp --model lightgcn \
      --lr 1e-3 --reg 1e-4 --run_dir runs/yelp/tce_lightgcn_N0_s1 --seed 1
"""
import argparse
import json
import os
import time

import numpy as np
import torch
import torch.nn.functional as F

from .backbone import Backbone, norm_adj, sample_negatives, valid_ndcg
from .data import load_split, to_csr
from .export import export_topk


def drop_rate_schedule(iteration, drop_rate, exponent, num_gradual):
    """DenoisingRec T_CE/main.py: linspace(0, drop_rate ** exponent, num_gradual), then constant drop_rate."""
    if iteration < num_gradual:
        return float(np.linspace(0, drop_rate ** exponent, num_gradual)[iteration])
    return drop_rate


def tce_loss(pos, neg, drop_rate):
    """DenoisingRec T_CE/loss.py loss_function on [pos; neg] with labels [1; 0], scaled like the kit's plain BCE."""
    y = torch.cat([pos, neg])
    t = torch.cat([torch.ones_like(pos), torch.zeros_like(neg)])
    loss = F.binary_cross_entropy_with_logits(y, t, reduction="none")
    ind_sorted = torch.argsort((loss * t).detach())
    num_remember = int((1 - drop_rate) * len(ind_sorted))
    keep = ind_sorted[:num_remember]
    return 2 * F.binary_cross_entropy_with_logits(y[keep], t[keep])


def rce_loss(pos, neg, alpha):
    """DenoisingRec R_CE/loss.py loss_function on [pos; neg] with labels [1; 0], scaled like the kit's plain BCE."""
    y = torch.cat([pos, neg])
    t = torch.cat([torch.ones_like(pos), torch.zeros_like(neg)])
    loss = F.binary_cross_entropy_with_logits(y, t, reduction="none")
    y_ = torch.sigmoid(y).detach()
    weight = torch.pow(y_, alpha) * t + torch.pow(1 - y_, alpha) * (1 - t)
    return 2 * (loss * weight).mean()


def plain_bce(pos, neg):
    return -(F.logsigmoid(pos) + F.logsigmoid(-neg)).mean()


def selftest():
    g = torch.Generator().manual_seed(0)
    pos, neg = torch.randn(1000, generator=g), torch.randn(1000, generator=g)
    a, b, c = plain_bce(pos, neg), tce_loss(pos, neg, 0.0), rce_loss(pos, neg, 0.0)
    assert torch.allclose(a, b, atol=1e-6) and torch.allclose(a, c, atol=1e-6), (a, b, c)
    # T-CE drops the largest positive losses only
    d = tce_loss(pos, neg, 0.2)
    assert d < a, (d, a)
    assert drop_rate_schedule(0, 0.2, 1, 100) == 0.0 and drop_rate_schedule(99, 0.2, 1, 100) == 0.2
    assert abs(drop_rate_schedule(50, 0.2, 1, 101) - 0.1) < 1e-9 and drop_rate_schedule(500, 0.2, 1, 100) == 0.2
    print("selftest ok: plain BCE", round(float(a), 6), "T-CE(0)", round(float(b), 6), "R-CE(0)", round(float(c), 6),
          "T-CE(0.2)", round(float(d), 6))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", choices=["tce", "rce"])
    ap.add_argument("--drop_rate", type=float, default=0.2, help="T-CE: final drop rate (epsilon_max)")
    ap.add_argument("--num_gradual", type=int, default=30000, help="T-CE: iterations to reach the drop rate (epsilon_N)")
    ap.add_argument("--exponent", type=float, default=1.0, help="T-CE: schedule exponent (authors' default 1)")
    ap.add_argument("--alpha", type=float, default=0.2, help="R-CE: weight exponent (beta in the paper)")
    ap.add_argument("--data")
    ap.add_argument("--train_file", default="train.tsv")
    ap.add_argument("--model", choices=["mf", "lightgcn"], default="lightgcn")
    ap.add_argument("--dim", type=int, default=64)
    ap.add_argument("--layers", type=int, default=3)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--reg", type=float, default=1e-4)
    ap.add_argument("--batch", type=int, default=2048)
    ap.add_argument("--epochs", type=int, default=300)
    ap.add_argument("--patience", type=int, default=20)
    ap.add_argument("--eval_every", type=int, default=1)
    ap.add_argument("--select", choices=["valid_clean", "valid_noisy"], default="valid_clean")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--run_dir")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--no_export", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    assert a.method and a.data and a.run_dir, "--method, --data and --run_dir are required"

    torch.manual_seed(a.seed)
    np.random.seed(a.seed)
    rng = np.random.default_rng(a.seed)
    os.makedirs(a.run_dir, exist_ok=True)
    dev = torch.device(a.device)
    meta, train, valid_clean, valid_noisy, test = load_split(a.data, a.train_file)
    nu, ni = meta["n_users"], meta["n_items"]
    train = train.drop_duplicates(["user", "item"])
    train_csr = to_csr(train, nu, ni)
    truths = {"valid_clean": to_csr(valid_clean, nu, ni), "valid_noisy": to_csr(valid_noisy, nu, ni)}
    keys = np.sort(train["user"].values.astype(np.int64) * ni + train["item"].values)
    adj = norm_adj(train_csr, dev) if a.model == "lightgcn" else None
    model = Backbone(nu, ni, a.dim, a.model, a.layers, adj).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=a.lr)
    users_all, items_all = train["user"].values, train["item"].values

    if dev.type == "cuda":
        torch.cuda.reset_peak_memory_stats(dev)
    t0 = time.time()
    best, best_epoch, bad, it = -1.0, 0, 0, 0
    hf = open(os.path.join(a.run_dir, "history.jsonl"), "w")
    for epoch in range(1, a.epochs + 1):
        model.train()
        perm = rng.permutation(len(users_all))
        neg_all = sample_negatives(users_all[perm], ni, keys, rng)
        tot = 0.0
        for s in range(0, len(perm), a.batch):
            idx = perm[s:s + a.batch]
            u = torch.tensor(users_all[idx], device=dev)
            p = torch.tensor(items_all[idx], device=dev)
            n = torch.tensor(neg_all[s:s + a.batch], device=dev)
            U, I = model.propagate()
            su, sp, sn = U[u], I[p], I[n]
            pos, negs = (su * sp).sum(1), (su * sn).sum(1)
            if a.method == "tce":
                loss = tce_loss(pos, negs, drop_rate_schedule(it, a.drop_rate, a.exponent, a.num_gradual))
            else:
                loss = rce_loss(pos, negs, a.alpha)
            reg = (model.user(u).pow(2).sum() + model.item(p).pow(2).sum() + model.item(n).pow(2).sum()) / (2 * len(idx))
            loss = loss + a.reg * reg
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item() * len(idx)
            it += 1
        if epoch % a.eval_every:
            continue
        model.eval()
        v = valid_ndcg(model, train_csr, truths, dev)
        rec = {"epoch": epoch, "iteration": it, "loss": tot / len(perm), "seconds": round(time.time() - t0, 1),
               **{f"{k}_ndcg@20": x for k, x in v.items()}}
        hf.write(json.dumps(rec) + "\n"); hf.flush()
        print(rec, flush=True)
        if v[a.select] > best:
            best, best_epoch, bad = v[a.select], epoch, 0
            torch.save(model.state_dict(), os.path.join(a.run_dir, "best.pt"))
        else:
            bad += 1
            if bad >= a.patience:
                break
    train_seconds = time.time() - t0
    model.load_state_dict(torch.load(os.path.join(a.run_dir, "best.pt"), map_location=dev, weights_only=True))
    model.eval()
    t1 = time.time()
    if not a.no_export:
        with torch.no_grad():
            U, I = model.propagate()
        export_topk(lambda users: U[users] @ I.T, a.data, a.run_dir, a.train_file, device=dev)
    info = {**vars(a), "loss": "bce", "best_valid_ndcg@20": best, "best_epoch": best_epoch, "epochs_run": epoch,
            "iterations": it, "train_seconds": round(train_seconds, 1), "export_seconds": round(time.time() - t1, 1),
            "peak_gpu_mb": round(torch.cuda.max_memory_allocated(dev) / 2 ** 20) if dev.type == "cuda" else None}
    json.dump(info, open(os.path.join(a.run_dir, "run.json"), "w"), indent=2)
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
