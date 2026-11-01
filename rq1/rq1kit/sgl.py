"""SGL-ED (Wu et al., Self-supervised Graph Learning for Recommendation, SIGIR 2021) on the kit's LightGCN: Part C
adapter (code-change class 4). Ported from the authors' PyTorch code, github.com/wujcan/SGL-Torch @ c563288
(model/general_recommender/SGL.py: _LightGCN.forward, SGL.create_adj_mat, SGL.train_model, conf/SGL.ini).

What the authors' code does, and this port does the same (augmentation type ED, mode both_side):
  * Every epoch two sub-graphs are drawn: int(n_edges * (1 - ssl_ratio)) training edges kept, uniformly without
    replacement, and the symmetric normalisation D^-1/2 A D^-1/2 recomputed on the kept edges. With ssl_ratio 0 the full
    graph is used for both views.
  * Every batch propagates three times (full graph, view 1, view 2) through the same embedding tables.
  * Loss, summed over the batch as in the authors' code:
        BPR           -sum log sigmoid(u.p - u.n)                       on the full-graph embeddings
        InfoNCE       sum_users logsumexp((z1_u . z2_all - z1_u . z2_u) / tau) + the same for the batch's positive items,
                      with z the L2-normalised view embeddings and the negatives all users (items) of the other view
        L2            reg * (|e_u|^2 + |e_p|^2 + |e_n|^2) / 2           on the raw embeddings of the batch
        loss = BPR + ssl_reg * InfoNCE + L2
  * Authors' defaults: ssl_reg 0.1, ssl_temp 0.2, ssl_ratio 0.1, reg 1e-4, lr 1e-3, 3 layers, dim 64, batch 2048.

Kept from the kit, recorded as adaptations: the kit's Backbone and its initialisation (authors: xavier uniform), the
kit's negative sampler (uniform over items outside the user's training items, as theirs), selection of the epoch on
clean-validation NDCG@20 every epoch with patience 20 (authors: the test set, every epoch, patience 10; finding 2 of
the report), seed, export. The kit passes the plain model's tuned --lr and --reg, as for every method.

  python -m rq1kit.sgl --ssl_reg 0.1 --ssl_temp 0.2 --ssl_ratio 0.1 --data data/yelp --lr 1e-3 --reg 1e-4 \
      --run_dir runs/yelp/sgl_lightgcn_N0_s1 --seed 1
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


def propagate_with(model, adj):
    """The backbone's LightGCN propagation (mean over layers 0..L) on another adjacency matrix."""
    ego = torch.cat([model.user.weight, model.item.weight])
    out, x = [ego], ego
    for _ in range(model.layers):
        x = torch.sparse.mm(adj, x)
        out.append(x)
    x = torch.stack(out).mean(0)
    return x[: model.nu], x[model.nu:]


def edge_dropout_adj(users, items, nu, ni, ratio, gen):
    """Authors' create_adj_mat(is_subgraph=True, aug_type='ed'): keep int(n * (1 - ratio)) edges drawn without
    replacement, then symmetric normalisation of the kept graph (degree 0 gives weight 0)."""
    n = len(users)
    keep = torch.randperm(n, device=users.device, generator=gen)[: int(n * (1 - ratio))]
    r = torch.cat([users[keep], items[keep] + nu])
    c = torch.cat([items[keep] + nu, users[keep]])
    deg = torch.bincount(r, minlength=nu + ni).float()
    w = 1.0 / torch.sqrt(deg[r] * deg[c])
    return torch.sparse_coo_tensor(torch.stack([r, c]), w, (nu + ni, nu + ni)).coalesce()


def sgl_loss(U, I, U1, I1, U2, I2, u, p, n, ssl_reg, tau, reg, raw_u, raw_p, raw_n):
    """Authors' loss for one batch (sums over the batch). U, I: full-graph embeddings; U1, I1, U2, I2: view
    embeddings (not yet normalised); raw_*: the batch's rows of the embedding tables."""
    U1, I1, U2, I2 = (F.normalize(x, dim=1) for x in (U1, I1, U2, I2))
    eu, ep, en = U[u], I[p], I[n]
    bpr = -F.logsigmoid((eu * ep).sum(1) - (eu * en).sum(1)).sum()
    u1, u2, i1, i2 = U1[u], U2[u], I1[p], I2[p]
    ssl_u = (u1 @ U2.T) - (u1 * u2).sum(1, keepdim=True)
    ssl_i = (i1 @ I2.T) - (i1 * i2).sum(1, keepdim=True)
    infonce = torch.logsumexp(ssl_u / tau, 1).sum() + torch.logsumexp(ssl_i / tau, 1).sum()
    l2 = (raw_u.pow(2).sum() + raw_p.pow(2).sum() + raw_n.pow(2).sum()) / 2
    return bpr + ssl_reg * infonce + reg * l2, bpr, infonce


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ssl_reg", type=float, default=0.1, help="lambda1: weight of the contrastive loss (paper 0.005-1.0)")
    ap.add_argument("--ssl_temp", type=float, default=0.2, help="tau: InfoNCE temperature (paper 0.1-1.0)")
    ap.add_argument("--ssl_ratio", type=float, default=0.1, help="rho: edge dropout ratio (paper 0-0.5)")
    ap.add_argument("--data", required=True)
    ap.add_argument("--train_file", default="train.tsv")
    ap.add_argument("--model", choices=["lightgcn"], default="lightgcn")
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
    gen = torch.Generator(device=dev).manual_seed(a.seed)
    meta, train, valid_clean, valid_noisy, test = load_split(a.data, a.train_file)
    nu, ni = meta["n_users"], meta["n_items"]
    train = train.drop_duplicates(["user", "item"])
    train_csr = to_csr(train, nu, ni)
    truths = {"valid_clean": to_csr(valid_clean, nu, ni), "valid_noisy": to_csr(valid_noisy, nu, ni)}
    keys = np.sort(train["user"].values.astype(np.int64) * ni + train["item"].values)
    adj = norm_adj(train_csr, dev)
    model = Backbone(nu, ni, a.dim, "lightgcn", a.layers, adj).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=a.lr)
    users_all, items_all = train["user"].values, train["item"].values
    ut, it = torch.tensor(users_all, device=dev), torch.tensor(items_all, device=dev)

    if dev.type == "cuda":
        torch.cuda.reset_peak_memory_stats(dev)
    t0 = time.time()
    best, best_epoch, bad = -1.0, 0, 0
    hf = open(os.path.join(a.run_dir, "history.jsonl"), "w")
    for epoch in range(1, a.epochs + 1):
        model.train()
        if a.ssl_ratio > 0:
            g1 = edge_dropout_adj(ut, it, nu, ni, a.ssl_ratio, gen)
            g2 = edge_dropout_adj(ut, it, nu, ni, a.ssl_ratio, gen)
        else:
            g1 = g2 = adj
        perm = rng.permutation(len(users_all))
        neg_all = sample_negatives(users_all[perm], ni, keys, rng)
        tot = 0.0
        for s in range(0, len(perm), a.batch):
            idx = perm[s:s + a.batch]
            u = torch.tensor(users_all[idx], device=dev)
            p = torch.tensor(items_all[idx], device=dev)
            n = torch.tensor(neg_all[s:s + a.batch], device=dev)
            U, I = model.propagate()
            U1, I1 = propagate_with(model, g1)
            U2, I2 = propagate_with(model, g2)
            loss, _, _ = sgl_loss(U, I, U1, I1, U2, I2, u, p, n, a.ssl_reg, a.ssl_temp, a.reg,
                                  model.user(u), model.item(p), model.item(n))
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item()
        if epoch % a.eval_every:
            continue
        model.eval()
        v = valid_ndcg(model, train_csr, truths, dev)
        rec = {"epoch": epoch, "loss": tot / len(perm), "seconds": round(time.time() - t0, 1),
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
    info = {**vars(a), "loss": "bpr+infonce", "best_valid_ndcg@20": best, "best_epoch": best_epoch,
            "epochs_run": epoch, "train_seconds": round(train_seconds, 1), "export_seconds": round(time.time() - t1, 1),
            "peak_gpu_mb": round(torch.cuda.max_memory_allocated(dev) / 2 ** 20) if dev.type == "cuda" else None}
    json.dump(info, open(os.path.join(a.run_dir, "run.json"), "w"), indent=2)
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
