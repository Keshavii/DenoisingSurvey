"""PLD (Zhang et al., Personalized Denoising Implicit Feedback for Robust Recommender System, WWW 2025) on the
kit's backbones: Part C adapter (code-change class 4). Ported from the authors' code, github.com/Kaike-Zhang/PLD
@ dd7b14f (utls/trainer.py PLDCFTrainer._train_epoch, utls/mydataset.py get_train_batch, utls/model_config.py).

What the authors' code does, and this port does the same: from epoch begin_adv on (authors: 5, 0-based), for every
training example the user's positive is resampled. k candidate positives are drawn from the user's training items
(without replacement when the user has at least k, otherwise with replacement), each is scored with BPR against the
example's one negative under the current model (no gradient), and one candidate is drawn with probability
softmax(-loss / temperature). The model is then trained on (user, chosen candidate, negative) with BPR.

Kept from the kit, recorded as adaptations: the order of training examples (one pass over the training
interactions per epoch, as every kit method; the authors draw users uniformly at random), Adam with the kit's L2
term (authors: AdamW with default weight decay plus an L2 term), selection on clean-validation NDCG@20, export.
With --begin_adv beyond the last epoch, PLD trains exactly like Plain-BPR (checked by tests/test_pld.py).

  python -m rq1kit.pld --item_num 5 --temp 0.1 --data data/yelp --model lightgcn --lr 1e-3 --reg 1e-4 \
      --run_dir runs/yelp/pld_lightgcn_N0_s1 --seed 1
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


def sample_candidates(users, k, indptr, indices, rng):
    """k candidate positives per user from its training items: a uniform k-subset (Floyd's algorithm) when the user
    has at least k items, k draws with replacement otherwise (authors: np.random.choice(items, k, replace=...))."""
    deg = indptr[users + 1] - indptr[users]
    big = deg >= k
    sel = np.empty((len(users), k), dtype=np.int64)
    for step in range(k):
        j = deg - k + step
        t = (rng.random(len(users)) * np.maximum(j + 1, 1)).astype(np.int64)
        clash = (sel[:, :step] == t[:, None]).any(1) if step else np.zeros(len(users), bool)
        sel[:, step] = np.where(clash, j, t)
    small = (rng.random((len(users), k)) * deg[:, None]).astype(np.int64)
    off = np.where(big[:, None], sel, small)
    return indices[indptr[users][:, None] + off]


def pld_select(Ud, Id, u, cand, n, temp):
    """Authors' pre-selection: BPR loss softplus(neg - pos) of each candidate, sample one with softmax(-loss / temp)."""
    with torch.no_grad():
        eu = Ud[u]
        pos = (eu[:, None, :] * Id[cand]).sum(-1)
        neg = (eu * Id[n]).sum(1, keepdim=True)
        prob = torch.softmax(-F.softplus(neg - pos) / temp, dim=1)
        pick = torch.multinomial(prob, 1).squeeze(1)
    return cand.gather(1, pick[:, None]).squeeze(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--item_num", type=int, default=5, help="k: candidate pool size (authors' default 5)")
    ap.add_argument("--temp", type=float, default=0.1, help="tau: sampling temperature (authors' default 0.1)")
    ap.add_argument("--begin_adv", type=int, default=5, help="first 0-based epoch with resampling (authors: 5)")
    ap.add_argument("--data", required=True)
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
    ap.add_argument("--run_dir", required=True)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--no_export", action="store_true")
    a = ap.parse_args()

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
    indptr, indices = train_csr.indptr.astype(np.int64), train_csr.indices.astype(np.int64)

    if dev.type == "cuda":
        torch.cuda.reset_peak_memory_stats(dev)
    t0 = time.time()
    best, best_epoch, bad = -1.0, 0, 0
    hf = open(os.path.join(a.run_dir, "history.jsonl"), "w")
    for epoch in range(1, a.epochs + 1):
        resample = epoch - 1 >= a.begin_adv
        model.train()
        perm = rng.permutation(len(users_all))
        neg_all = sample_negatives(users_all[perm], ni, keys, rng)
        tot = 0.0
        for s in range(0, len(perm), a.batch):
            idx = perm[s:s + a.batch]
            u = torch.tensor(users_all[idx], device=dev)
            n = torch.tensor(neg_all[s:s + a.batch], device=dev)
            U, I = model.propagate()
            if resample:
                cand = torch.tensor(sample_candidates(users_all[idx], a.item_num, indptr, indices, rng), device=dev)
                p = pld_select(U.detach(), I.detach(), u, cand, n, a.temp)
            else:
                p = torch.tensor(items_all[idx], device=dev)
            su, sp, sn = U[u], I[p], I[n]
            loss = -F.logsigmoid((su * sp).sum(1) - (su * sn).sum(1)).mean()
            reg = (model.user(u).pow(2).sum() + model.item(p).pow(2).sum() + model.item(n).pow(2).sum()) / (2 * len(idx))
            loss = loss + a.reg * reg
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item() * len(idx)
        if epoch % a.eval_every:
            continue
        model.eval()
        v = valid_ndcg(model, train_csr, truths, dev)
        rec = {"epoch": epoch, "loss": tot / len(perm), "resample": resample, "seconds": round(time.time() - t0, 1),
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
    info = {**vars(a), "loss": "bpr", "best_valid_ndcg@20": best, "best_epoch": best_epoch, "epochs_run": epoch,
            "train_seconds": round(train_seconds, 1), "export_seconds": round(time.time() - t1, 1),
            "peak_gpu_mb": round(torch.cuda.max_memory_allocated(dev) / 2 ** 20) if dev.type == "cuda" else None}
    json.dump(info, open(os.path.join(a.run_dir, "run.json"), "w"), indent=2)
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
