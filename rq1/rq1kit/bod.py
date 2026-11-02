"""BOD (Wang et al., Efficient Bi-level Optimization for Recommendation Denoising, KDD 2023) on the kit's LightGCN:
Part C adapter (code-change class 4). Ported from the authors' code, github.com/CoderWZW/BOD @ bab641b
(model/graph/BOD.py: BOD.train, match_loss, distance_wb, GraphGenerator_VAE; util/loss_torch.py; conf/BOD.conf).

What the authors' code does, and this port does the same:
  * A denoising generator g(u, i) in (0, 1): MLP on the concatenated user and item embeddings,
    Linear(2d, 64) - ReLU - Linear(64, 64) - Linear(64, 1) - sigmoid. It is the sample weight of a pair.
  * Every epoch, an inner pass over all training batches updates the recommender only (generator weights detached):
        loss = w_bpr x BPR_w + w_align x ALIGN_w + w_unif x UNIF
        BPR_w   = mean -log(1e-7 + sigmoid(g(u,p) u.p - g(u,n) u.n))     (the weights scale the scores)
        ALIGN_w = mean g(u,p) |u/|u| - p/|p||^2
        UNIF    = mean of the log-mean-exp uniformity of the batch's user, user, positive and negative embeddings
  * Then outer_loop generator steps (one gradient-matching step on a random batch): the generator is trained so that
    the gradient of the alignment loss (weighted by g(u,i)) w.r.t. the recommender's embeddings points in the same
    direction as the gradient of the BPR loss (weighted by g(u,u) for the positive and g(u,n) for the negative):
    loss = sum over the two embedding tables of sum_over_dims (1 - cos(grad_real, grad_syn)) + generator_reg x
    (|u| + |i|). Second-order gradients through the recommender's propagation are kept (create_graph).
  * Authors' defaults: LightGCN 2 layers, dim 64, batch 512, lr 1e-3, generator lr 1e-3, generator reg 1e-3,
    weights 1 / 1 / 0.5, inner_loop 1, outer_loop 1, 100 epochs.

Kept from the kit, recorded as adaptations: the kit's Backbone and its initialisation (authors: xavier uniform), batch
2048 for the inner pass and for the outer step (authors: 512; 4.6k steps per epoch on Amazon-Book otherwise),
selection of the epoch on clean-validation NDCG@20 every epoch with patience 20 (authors: the test set every 5 epochs,
finding 2 of the report), the kit's negative sampler (uniform over items outside the user's training items, as theirs;
their outer step also samples random training edges), seed, export. The kit passes the plain model's tuned --lr
(--lr_mult scales it); --reg is accepted and NOT used (the authors have no embedding penalty on the recommender).

  python -m rq1kit.bod --weight_uniformity 0.5 --generator_lr 1e-3 --data data/yelp --lr 1e-3 \
      --run_dir runs/yelp/bod_lightgcn_N0_s1 --seed 1
"""
import argparse
import json
import os
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .backbone import Backbone, norm_adj, sample_negatives, valid_ndcg
from .data import load_split, to_csr
from .export import export_topk


class Generator(nn.Module):
    """Authors' GraphGenerator_VAE (the layers they define but never call are not created)."""

    def __init__(self, dim=64):
        super().__init__()
        self.encoder = nn.Linear(dim * 2, 64)
        self.fc_encoder = nn.Linear(64, 64)
        self.fc_decode = nn.Linear(64, 1)

    def forward(self, user_e, item_e):
        h = torch.relu(self.encoder(torch.cat((user_e, item_e), dim=1)))
        return torch.sigmoid(self.fc_decode(self.fc_encoder(h)))


def bpr_loss_weight(u, p, n, w_pos, w_neg):
    pos = w_pos * torch.mul(u, p).sum(dim=1)
    neg = w_neg * torch.mul(u, n).sum(dim=1)
    return torch.mean(-torch.log(10e-8 + torch.sigmoid(pos - neg)))


def alignment_loss_weight(x, y, weight, alpha=2):
    x, y = F.normalize(x, dim=-1), F.normalize(y, dim=-1)
    return (weight * (x - y).norm(p=2, dim=1).pow(alpha)).mean()


def uniformity_loss(x, t=2):
    x = F.normalize(x, dim=-1)
    return torch.pdist(x, p=2).pow(2).mul(-t).exp().mean().log()


def distance_wb(gwr, gws):
    """Authors' distance for 2-d gradients: transposed, 1 - cosine over the long axis, summed over the embedding dims."""
    gwr, gws = gwr.T, gws.T
    return torch.sum(1 - torch.sum(gwr * gws, dim=-1) / (torch.norm(gwr, dim=-1) * torch.norm(gws, dim=-1) + 0.000001))


def match_loss(gw_syn, gw_real):
    return sum(distance_wb(r, s) for r, s in zip(gw_real, gw_syn))


def inner_loss(eu, ep, en, gen, w_bpr, w_align, w_unif):
    """Recommender loss of one inner batch; the generator's weights are constants here."""
    with torch.no_grad():
        wp, wn = gen(eu, ep), gen(eu, en)
    uni = (uniformity_loss(eu) + uniformity_loss(eu) + uniformity_loss(ep) + uniformity_loss(en)) / 4
    return w_bpr * bpr_loss_weight(eu, ep, en, wp, wn) + w_align * alignment_loss_weight(eu, ep, wp) + w_unif * uni


def outer_loss(params, eu, ep, en, gen, gen_reg):
    """Generator loss of one gradient-matching step. `params` are the recommender's embedding tables that eu/ep/en
    were computed from; the gradients are taken with create_graph so the generator receives second-order terms."""
    bpr_ol = bpr_loss_weight(eu, ep, en, gen(eu, eu), gen(eu, en))
    gw_real = torch.autograd.grad(bpr_ol, params, retain_graph=True, create_graph=True)
    align_ol = alignment_loss_weight(eu, ep, gen(eu, ep))
    gw_syn = torch.autograd.grad(align_ol, params, retain_graph=True, create_graph=True)
    return match_loss(gw_syn, gw_real) + gen_reg * (torch.norm(eu, p=2) + torch.norm(ep, p=2)), bpr_ol, align_ol


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generator_lr", type=float, default=1e-3)
    ap.add_argument("--generator_reg", type=float, default=1e-3)
    ap.add_argument("--weight_bpr", type=float, default=1.0)
    ap.add_argument("--weight_alignment", type=float, default=1.0)
    ap.add_argument("--weight_uniformity", type=float, default=0.5, help="authors' default 0.5")
    ap.add_argument("--inner_loop", type=int, default=1)
    ap.add_argument("--outer_loop", type=int, default=1)
    ap.add_argument("--lr_mult", type=float, default=1.0, help="Adam learning rate of the recommender = --lr x this")
    ap.add_argument("--reg", type=float, default=0.0, help="accepted for the pipeline; NOT used (see module doc)")
    ap.add_argument("--data", required=True)
    ap.add_argument("--train_file", default="train.tsv")
    ap.add_argument("--model", choices=["lightgcn"], default="lightgcn")
    ap.add_argument("--dim", type=int, default=64)
    ap.add_argument("--layers", type=int, default=2, help="authors' and paper's LightGCN depth")
    ap.add_argument("--lr", type=float, default=1e-3)
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
    adj = norm_adj(train_csr, dev)
    model = Backbone(nu, ni, a.dim, "lightgcn", a.layers, adj).to(dev)
    gen = Generator(a.dim).to(dev)
    lr_eff = a.lr * a.lr_mult
    opt = torch.optim.Adam(model.parameters(), lr=lr_eff)
    opt_gen = torch.optim.Adam(gen.parameters(), lr=a.generator_lr)
    users_all, items_all = train["user"].values, train["item"].values

    if dev.type == "cuda":
        torch.cuda.reset_peak_memory_stats(dev)
    t0 = time.time()
    best, best_epoch, bad = -1.0, 0, 0
    hf = open(os.path.join(a.run_dir, "history.jsonl"), "w")
    for epoch in range(1, a.epochs + 1):
        model.train()
        tot, count = 0.0, 0
        for _ in range(a.inner_loop):
            perm = rng.permutation(len(users_all))
            neg_all = sample_negatives(users_all[perm], ni, keys, rng)
            for s in range(0, len(perm), a.batch):
                idx = perm[s:s + a.batch]
                u = torch.tensor(users_all[idx], device=dev)
                p = torch.tensor(items_all[idx], device=dev)
                n = torch.tensor(neg_all[s:s + a.batch], device=dev)
                U, I = model.propagate()
                loss = inner_loss(U[u], I[p], I[n], gen, a.weight_bpr, a.weight_alignment, a.weight_uniformity)
                opt.zero_grad()
                loss.backward()
                opt.step()
                tot += loss.item() * len(idx)
                count += len(idx)
        gl = float("nan")
        for _ in range(a.outer_loop):
            idx = rng.integers(0, len(users_all), a.batch)
            neg = sample_negatives(users_all[idx], ni, keys, rng)
            u = torch.tensor(users_all[idx], device=dev)
            p = torch.tensor(items_all[idx], device=dev)
            n = torch.tensor(neg, device=dev)
            U, I = model.propagate()
            gloss, _, _ = outer_loss(list(model.parameters()), U[u], I[p], I[n], gen, a.generator_reg)
            opt_gen.zero_grad()
            gloss.backward()
            opt_gen.step()
            gl = gloss.item()
        if epoch % a.eval_every:
            continue
        model.eval()
        v = valid_ndcg(model, train_csr, truths, dev)
        rec = {"epoch": epoch, "loss": tot / max(count, 1), "generator_loss": gl, "seconds": round(time.time() - t0, 1),
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
    info = {**vars(a), "loss": "weighted-bpr+align+unif", "lr_effective": lr_eff, "best_valid_ndcg@20": best,
            "best_epoch": best_epoch, "epochs_run": epoch, "train_seconds": round(train_seconds, 1),
            "export_seconds": round(time.time() - t1, 1),
            "peak_gpu_mb": round(torch.cuda.max_memory_allocated(dev) / 2 ** 20) if dev.type == "cuda" else None}
    json.dump(info, open(os.path.join(a.run_dir, "run.json"), "w"), indent=2)
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
