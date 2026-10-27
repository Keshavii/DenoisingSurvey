"""DCF (He et al., Double Correction Framework for Denoising Recommendation, KDD 2024) on the kit's backbones:
Part C adapter (code-change class 4). Ported from the authors' code, github.com/bruno686/DCF @ 873cee3
(loss.py: soft_process, PLC_uncertain_discard; main.py: drop_rate_schedule, co_lambda_plan, the time-step memory).

Only the loss differs from rq1kit.backbone; data, backbone, negative sampling, regularisation, selection
(clean-validation NDCG@20), early stopping and the top-K export are the kit's.

What the authors' code does, and this port does the same:
  * per-sample BCE over positives and sampled negatives; positives' losses pass through the damping function
    log(1 + l + l^2/2); a running mean of that over the epochs of a time step (memory reset every time_step epochs);
  * a lower confidence bound co_lambda * (s + co_lambda * log(2s) / s^2) / ((n + 1) - co_lambda) is subtracted
    (s = epoch, n = how often the sample was in the low-loss part), co_lambda decaying linearly to 0;
  * the drop_rate share with the highest bound-adjusted loss is dropped, except the very highest
    relabel_ratio x drop_rate share, which is kept with its original label (drop rate schedule as in T-CE).

Where the code differs from the paper (kept, because Part C runs the authors' method as published in code):
  1. the running mean is stored by position in the epoch's shuffled order, not by interaction (main.py slices
     before_loss[start_point:stop_point] while the DataLoader shuffles), so it averages different interactions;
  2. no label is flipped: PLC_uncertain_discard returns train_mat unchanged and the kept high-loss samples
     keep label 1 (paper Eq. 7 flips them);
  3. the relabel ratio is constant (paper Eq. 5 grows it with the epoch).
Kit-specific choices (recorded): co_lambda decays over --schedule_epochs (default 100 = the tuning length; the
authors use their --epochs, default 10) and is 0 afterwards, so tuning and final runs see the same schedule;
batches are [positives; their negatives] as in every kit adapter; scaling matches the kit's plain BCE, so
drop_rate 0 with relabel_ratio 0 reproduces Plain-BCE exactly (checked by --selftest).

  python -m rq1kit.dcf --relabel_ratio 0.03 --co_lambda 0.001 --data data/yelp --model lightgcn \
      --lr 1e-3 --reg 1e-4 --run_dir runs/yelp/dcf_lightgcn_N0_s1 --seed 1
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
    """DCF main.py (same as DenoisingRec T_CE): linspace(0, drop_rate ** exponent, num_gradual), then drop_rate."""
    if iteration < num_gradual:
        return float(np.linspace(0, drop_rate ** exponent, num_gradual)[iteration])
    return drop_rate


def co_lambda_at(epoch0, co_lambda, schedule_epochs):
    """DCF main.py: co_lambda_plan = co_lambda * linspace(1, 0, epochs)[epoch]; 0 after the schedule."""
    return float(co_lambda * np.linspace(1, 0, schedule_epochs)[epoch0]) if epoch0 < schedule_epochs else 0.0


def soft_process(loss):
    return torch.log(1 + loss + loss * loss / 2)


def dcf_loss(pos, neg, drop_rate, s, sn, before, co_lambda, relabel_ratio):
    """DCF loss.py PLC_uncertain_discard on [pos; neg] with labels [1; 0], scaled like the kit's plain BCE.

    s: epoch counter (authors: epoch + 1 with 0-based epochs); sn, before: this batch's slice of the memory.
    Returns (loss, loss_mean for the memory, indices below the relabel threshold for the counter n)."""
    y = torch.cat([pos, neg])
    t = torch.cat([torch.ones_like(pos), torch.zeros_like(neg)])
    s = torch.tensor(float(s))
    co = torch.tensor(float(co_lambda))
    loss = F.binary_cross_entropy_with_logits(y, t, reduction="none")
    loss_mul = soft_process(loss * t)
    loss_mean = (before * s + loss_mul) / (s + 1)
    bound = co * (s + (co * torch.log(2 * s)) / (s * s)) / ((sn + 1) - co)
    loss_mul = F.relu(loss_mean.float() - bound.float())
    ind_sorted = torch.from_numpy(np.argsort(loss_mul.detach().cpu().numpy())).to(y.device)
    n = len(ind_sorted)
    num_remember = int((1 - drop_rate) * n)
    cut = int(((1 - relabel_ratio) + relabel_ratio * (1 - drop_rate)) * n)
    final_ind = torch.cat((ind_sorted[cut:], ind_sorted[:num_remember]))
    return 2 * F.binary_cross_entropy_with_logits(y[final_ind], t[final_ind]), loss_mean.detach(), ind_sorted[:cut]


def plain_bce(pos, neg):
    return -(F.logsigmoid(pos) + F.logsigmoid(-neg)).mean()


def selftest():
    g = torch.Generator().manual_seed(0)
    pos, neg = torch.randn(1000, generator=g), torch.randn(1000, generator=g)
    z, one = torch.zeros(2000), torch.ones(2000)
    a = plain_bce(pos, neg)
    b, _, _ = dcf_loss(pos, neg, 0.0, 1, one, z, 1e-4, 0.0)
    assert torch.allclose(a, b, atol=1e-6), (a, b)
    # relabel 0, co_lambda 0, empty memory: same kept set as T-CE (ranking by a monotone function of the loss)
    from .adt import tce_loss
    c, _, _ = dcf_loss(pos, neg, 0.2, 1, one, z, 0.0, 0.0)
    assert torch.allclose(c, tce_loss(pos, neg, 0.2), atol=1e-6), (c, tce_loss(pos, neg, 0.2))
    # relabel keeps back the top relabel x drop share
    d, mean, low = dcf_loss(pos, neg, 0.2, 1, one, z, 0.0, 0.25)
    assert len(low) == int((0.75 + 0.25 * 0.8) * 2000) and d > c
    assert co_lambda_at(0, 0.01, 100) == 0.01 and co_lambda_at(99, 0.01, 100) == 0.0 and co_lambda_at(150, 0.01, 100) == 0.0
    print("selftest ok: plain BCE", round(float(a), 6), "DCF(0,0)", round(float(b), 6), "DCF(0.2, R 0) = T-CE(0.2)",
          round(float(c), 6), "DCF(0.2, R 0.25)", round(float(d), 6))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drop_rate", type=float, default=0.2, help="authors' default")
    ap.add_argument("--num_gradual", type=int, default=30000, help="authors' default")
    ap.add_argument("--exponent", type=float, default=1.0)
    ap.add_argument("--relabel_ratio", type=float, default=0.05, help="R in the paper (authors' default 0.05)")
    ap.add_argument("--co_lambda", type=float, default=1e-4, help="sigma^2 in the paper (authors' default 1e-4)")
    ap.add_argument("--time_step", type=int, default=3, help="v in the paper: epochs per memory window")
    ap.add_argument("--schedule_epochs", type=int, default=100, help="epochs over which co_lambda decays to 0")
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
    assert a.data and a.run_dir, "--data and --run_dir are required"

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
    n_pos = len(users_all)

    if dev.type == "cuda":
        torch.cuda.reset_peak_memory_stats(dev)
    t0 = time.time()
    best, best_epoch, bad, it = -1.0, 0, 0, 0
    before = sn = None
    hf = open(os.path.join(a.run_dir, "history.jsonl"), "w")
    for epoch in range(1, a.epochs + 1):
        e0 = epoch - 1  # the authors' 0-based epoch
        if e0 % a.time_step == 0:  # "Time step initializing": memory reset
            before = torch.zeros(2 * n_pos, device=dev)
            sn = torch.ones(2 * n_pos, device=dev, dtype=torch.float64)
        new_before = torch.zeros(2 * n_pos, device=dev)
        touched = torch.zeros(2 * n_pos, device=dev, dtype=torch.bool)
        co = co_lambda_at(e0, a.co_lambda, a.schedule_epochs)
        model.train()
        perm = rng.permutation(n_pos)
        neg_all = sample_negatives(users_all[perm], ni, keys, rng)
        tot = 0.0
        for s in range(0, n_pos, a.batch):
            idx = perm[s:s + a.batch]
            u = torch.tensor(users_all[idx], device=dev)
            p = torch.tensor(items_all[idx], device=dev)
            n = torch.tensor(neg_all[s:s + a.batch], device=dev)
            U, I = model.propagate()
            su, sp, sn_ = U[u], I[p], I[n]
            pos, negs = (su * sp).sum(1), (su * sn_).sum(1)
            sl = slice(2 * s, 2 * s + 2 * len(idx))  # positions in this epoch's order, as in the authors' code
            loss, mean, low = dcf_loss(pos, negs, drop_rate_schedule(it, a.drop_rate, a.exponent, a.num_gradual),
                                       epoch, sn[sl], before[sl], co, a.relabel_ratio)
            new_before[sl] = mean
            touched[2 * s + low] = True
            reg = (model.user(u).pow(2).sum() + model.item(p).pow(2).sum() + model.item(n).pow(2).sum()) / (2 * len(idx))
            loss = loss + a.reg * reg
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item() * len(idx)
            it += 1
        before = new_before
        sn = sn + touched.double()
        if epoch % a.eval_every:
            continue
        model.eval()
        v = valid_ndcg(model, train_csr, truths, dev)
        rec = {"epoch": epoch, "iteration": it, "loss": tot / n_pos, "co_lambda": co, "seconds": round(time.time() - t0, 1),
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
