"""DeCA (Wang et al., Learning Robust Recommenders through Cross-Model Agreement, WWW 2022) on the kit's backbones:
Part C adapter (code-change class 4). Ported from the authors' code, github.com/wangyu-ustc/DeCA @ 8b04aa8
(train.py: TrainModel.RS_train [variational branch], positive_loss_function, negative_loss_function, KL_loss, KL;
model.py: MF; configs.py; main.py).

What the authors' code does, and this port does the same (method DeCA, not DeCAp):
  * Four networks: the recommender f (sigmoid of the user-item score), an auxiliary MF model g trained jointly (the
    "other" model in the cross-model agreement), and two hypothesis MF models h1 (denoise positives, "DP") and h2 (denoise
    negatives, "DN"). All are probability models: sigmoid(u . i).
  * Per batch of positives with one sampled negative each, with p = g(u, i) and q = f(u, i), x = log(x + 1e-5):
        KL(p, q) = p log p - p log q + (1-p) log(1-p) - (1-p) log(1-q)
        agree    = alpha KL(g, f) + (1 - alpha) KL(f, g)
        positives: agree - [log h1 (1-q)                     if DP]      negatives: agree - [log(1-h1)(1-q) - C1 q   if DP]
                          [log h2 q - C2 (1-q)               if DN]                        [log(1-h2) q             if DN]
                          [log(1-h1)(1-q) + log(1-h2) q      if both]                      [same as positives       if both]
        loss = mean(positives) + NSR x mean(negatives)  + regularisation
  * The mode alternates every batch: the first batch uses 'both' (h1 and h2 both step), then DP, DN, DP, ... ; h1 steps in
    'both' and DP, h2 in 'both' and DN; g steps every batch; f steps every batch. All Adam, lr 1e-3 (h1, h2, g).
  * Authors' defaults: embedding size 32 for g, h1, h2; C1, C2 in {10, 100, 1000}; alpha in {0, 0.5, 1} (per dataset).

Kept from the kit, recorded as adaptations: the recommender is the kit's Backbone (MF or LightGCN, dim 64) with the kit's
initialisation, its tuned --lr and --reg (authors: a penalty on every parameter of f x lambda0), the kit's batch
construction ([positives; one sampled negative each], uniform over items outside the user's training items), the kit's
selection of the epoch on clean-validation NDCG@20 with patience 20 (authors: fixed epoch counts or early stopping on the
BCE of validation pairs), seed, export. g, h1, h2 use the authors' MF with std 0.01 initialisation and lr --lr_aux 1e-3.

  python -m rq1kit.deca --C_1 100 --C_2 100 --alpha 0.5 --data data/yelp --model lightgcn --lr 1e-3 --reg 1e-4 \
      --run_dir runs/yelp/deca_lightgcn_N0_s1 --seed 1
"""
import argparse
import json
import os
import time

import numpy as np
import torch
import torch.nn as nn

from .backbone import Backbone, norm_adj, sample_negatives, valid_ndcg
from .data import load_split, to_csr
from .export import export_topk


def log(x):
    return torch.log(x + 1e-5)


def kl(p1, p2):
    return p1 * log(p1) - p1 * log(p2) + (1 - p1) * log(1 - p1) - (1 - p1) * log(1 - p2)


def agreement(g, f, alpha):
    return kl(g, f) * alpha + kl(f, g) * (1 - alpha)


def positive_term(kind, h1, h2, q, c2):
    if kind == "DP":
        return log(h1) * (1 - q)
    if kind == "DN":
        return log(h2) * q - c2 * (1 - q)
    return log(1 - h1) * (1 - q) + log(1 - h2) * q


def negative_term(kind, h1, h2, q, c1):
    if kind == "DP":
        return log(1 - h1) * (1 - q) - q * c1
    if kind == "DN":
        return log(1 - h2) * q
    return log(1 - h1) * (1 - q) + log(1 - h2) * q


def deca_loss(kind, f_pos, f_neg, g_pos, g_neg, h1_pos, h1_neg, h2_pos, h2_neg, c1, c2, alpha, nsr=1):
    pos = torch.mean(agreement(g_pos, f_pos, alpha) - positive_term(kind, h1_pos, h2_pos, f_pos, c2))
    neg = torch.mean(agreement(g_neg, f_neg, alpha) - negative_term(kind, h1_neg, h2_neg, f_neg, c1))
    return pos + neg * nsr


def next_kind(kind, iterative=True):
    """Authors' _on_iteration_end: 'both' (first batch) -> DP -> DN -> DP ..."""
    return ("DN" if kind == "DP" else "DP") if iterative else kind


class ProbMF(nn.Module):
    """Authors' MF (model.py): sigmoid of the dot product, normal(0, 0.01) initialisation."""

    def __init__(self, nu, ni, dim):
        super().__init__()
        self.user_embedding = nn.Embedding(nu, dim)
        self.item_embedding = nn.Embedding(ni, dim)
        nn.init.normal_(self.user_embedding.weight, std=0.01)
        nn.init.normal_(self.item_embedding.weight, std=0.01)

    def forward(self, u, i):
        return torch.sigmoid((self.user_embedding(u) * self.item_embedding(i)).sum(1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--C_1", type=float, default=100.0, help="negative-side penalty (paper {10, 100, 1000})")
    ap.add_argument("--C_2", type=float, default=100.0, help="positive-side penalty (paper {10, 100, 1000})")
    ap.add_argument("--alpha", type=float, default=0.5, help="weight of KL(g, f) vs KL(f, g) (paper {0, 0.5, 1})")
    ap.add_argument("--denoise_type", choices=["both", "DP", "DN"], default="both", help="authors' default both")
    ap.add_argument("--aux_dim", type=int, default=32, help="embedding size of g, h1, h2 (authors' emb_dim)")
    ap.add_argument("--lr_aux", type=float, default=1e-3)
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
    a = ap.parse_args()
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
    g, h1, h2 = (ProbMF(nu, ni, a.aux_dim).to(dev) for _ in range(3))
    opt = torch.optim.Adam(model.parameters(), lr=a.lr)
    opt_g, opt_h1, opt_h2 = (torch.optim.Adam(m.parameters(), lr=a.lr_aux) for m in (g, h1, h2))
    users_all, items_all = train["user"].values, train["item"].values
    n_pos = len(users_all)
    kind = a.denoise_type

    if dev.type == "cuda":
        torch.cuda.reset_peak_memory_stats(dev)
    t0 = time.time()
    best, best_epoch, bad = -1.0, 0, 0
    hf = open(os.path.join(a.run_dir, "history.jsonl"), "w")
    for epoch in range(1, a.epochs + 1):
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
            fp, fn = torch.sigmoid((U[u] * I[p]).sum(1)), torch.sigmoid((U[u] * I[n]).sum(1))
            loss = deca_loss(kind, fp, fn, g(u, p), g(u, n), h1(u, p), h1(u, n), h2(u, p), h2(u, n),
                             a.C_1, a.C_2, a.alpha)
            reg = (model.user(u).pow(2).sum() + model.item(p).pow(2).sum() + model.item(n).pow(2).sum()) / (2 * len(idx))
            loss = loss + a.reg * reg
            for o in (opt, opt_g, opt_h1, opt_h2):
                o.zero_grad()
            loss.backward()
            if kind != "DN":
                opt_h1.step()
            if kind != "DP":
                opt_h2.step()
            opt_g.step()
            opt.step()
            kind = next_kind(kind)
            tot += loss.item() * len(idx)
        if epoch % a.eval_every:
            continue
        model.eval()
        v = valid_ndcg(model, train_csr, truths, dev)
        rec = {"epoch": epoch, "loss": tot / n_pos, "seconds": round(time.time() - t0, 1),
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
    info = {**vars(a), "loss": "deca-kl", "best_valid_ndcg@20": best, "best_epoch": best_epoch, "epochs_run": epoch,
            "train_seconds": round(train_seconds, 1), "export_seconds": round(time.time() - t1, 1),
            "peak_gpu_mb": round(torch.cuda.max_memory_allocated(dev) / 2 ** 20) if dev.type == "cuda" else None}
    json.dump(info, open(os.path.join(a.run_dir, "run.json"), "w"), indent=2)
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
