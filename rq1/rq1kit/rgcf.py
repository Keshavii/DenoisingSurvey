"""RGCF (Tian et al., Learning to Denoise Unreliable Interactions for Graph Collaborative Filtering, SIGIR 2022):
Part C adapter (code-change class 4). Ported from the authors' code, github.com/ChangxinTian/RGCF @ a7dec98
(rgcf.py: RGCF.get_sim_adj, get_aug_adj, forward, ssl_forward, calculate_loss; config/model-rgcf.yaml).

What the authors' code does, and this port does the same:
  * No free embeddings. The user representation is the interaction row times a learnable matrix of shape n_items x dim
    (the sum of the user's item vectors); the item representation is the transposed row times a n_users x dim matrix.
  * Graph denoising, recomputed in every training batch with gradients: the reliability of each training edge is the
    cosine similarity of its user and item representations, mapped to (sim + 1) / 2; reliabilities below the pruning
    threshold are set to 0 (hard denoising), the rest are kept as edge weights (soft denoising) after row
    normalisation D^-1 A. LightGCN propagation on that graph, mean over layers 0..K.
  * Diversity module (MIM): a pool of 10 x aug_ratio x nnz / 2 random user-item pairs; the most reliable
    aug_ratio x nnz / 2 of them (largest dot product of the representations) are added to the (detached) denoised graph
    with the median edge weight, normalised by the row degree (their code applies the row degree on both sides); a second propagation; InfoNCE between the batch users' two
    representations against all users of the augmented view.
  * Loss = BPR (recbole: -log(1e-10 + sigmoid(pos - neg)), mean) + reg_weight x (sum of the norms of the batch's three
    representation matrices) / batch + MIM_weight x InfoNCE (summed over the batch).
  * Authors' defaults: 2 layers, dim 64, reg_weight 1e-5, prune_threshold 0.02, aug_ratio 0.1, MIM_weight 1e-6, tau 0.2,
    batch 4096, Adam, Xavier-uniform initialisation of the two matrices.

Kept from the kit, recorded as adaptations: 3 layers (paper tunes {2, 3}), selection of the epoch on clean-validation
NDCG@20 every epoch with patience 20 (authors: validation MRR@10, patience 10, 500 epochs), the kit's negative sampler
(uniform over items outside the user's training items, as theirs), seed, export. The kit passes the plain model's tuned
--lr; --lr_mult scales it (paper tunes the learning rate in [1e-5, 1e-3]); --reg is accepted and NOT used: the
authors fix reg_weight at 1e-5 with an unsquared-norm penalty that is not on the kit's scale (--reg_weight sets it).

  python -m rq1kit.rgcf --prune_threshold 0.02 --MIM_weight 1e-6 --data data/yelp --lr 5e-3 --lr_mult 0.1 \
      --run_dir runs/yelp/rgcf_lightgcn_N0_s1 --seed 1
"""
import argparse
import json
import os
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .backbone import sample_negatives, valid_ndcg
from .data import load_split, to_csr
from .export import export_topk


def sparse_sorted(idx, vals, size):
    """Sparse tensor whose indices are already sorted and unique (no re-sorting on every call)."""
    try:
        return torch.sparse_coo_tensor(idx, vals, size, is_coalesced=True)
    except TypeError:
        return torch.sparse_coo_tensor(idx, vals, size).coalesce()


class RGCF(nn.Module):
    def __init__(self, nu, ni, users, items, dim=64, layers=3, prune=0.02, tau=0.2, aug_ratio=0.1, device="cpu"):
        super().__init__()
        self.nu, self.ni, self.layers, self.prune, self.tau, self.aug_ratio = nu, ni, layers, prune, tau, aug_ratio
        self.dev = torch.device(device)
        self.user_linear = nn.Linear(ni, dim, bias=False)
        self.item_linear = nn.Linear(nu, dim, bias=False)
        nn.init.xavier_uniform_(self.user_linear.weight)
        nn.init.xavier_uniform_(self.item_linear.weight)
        users, items = np.asarray(users, dtype=np.int64), np.asarray(items, dtype=np.int64)
        order = np.lexsort((items, users))  # (user, item) order = the authors' coalesced interaction matrix
        users, items = users[order], items[order]
        t_perm = np.lexsort((users, items))  # same edges in (item, user) order = the transposed matrix
        u, i = torch.tensor(users), torch.tensor(items)
        tp = torch.tensor(t_perm)
        for name, t in (("u", u), ("i", i), ("t_perm", tp), ("rows", torch.cat([u, i[tp] + nu])), ("cols", torch.cat([i + nu, u[tp]]))):
            self.register_buffer(name, t, persistent=False)  # rows, cols: the authors' coalesced symmetric matrix order
        ones = torch.ones(len(u))
        self.inter = torch.sparse_coo_tensor(torch.stack([u, i]), ones, (nu, ni)).coalesce().to(self.dev)
        self.inter_t = torch.sparse_coo_tensor(torch.stack([i, u]), ones, (ni, nu)).coalesce().to(self.dev)
        self.adj_vals = None

    def feats(self):
        return (torch.sparse.mm(self.inter, self.user_linear.weight.t()),
                torch.sparse.mm(self.inter_t, self.item_linear.weight.t()))

    def sim_values(self, uf, itf, pruning, eps=1e-8):
        """Authors' get_sim_adj: reliability per directed edge, pruned, row-normalised."""
        un, inn = uf.norm(dim=1)[:, None], itf.norm(dim=1)[:, None]
        un = uf / torch.max(un, eps * torch.ones_like(un))
        inn = itf / torch.max(inn, eps * torch.ones_like(inn))
        sims = (un[self.u] * inn[self.i]).sum(1)
        v = torch.div(torch.add(torch.cat([sims, sims[self.t_perm]]), 1), 2)
        v = torch.where(v < pruning, torch.zeros_like(v), v) if pruning > 0 else v
        diags = torch.zeros(self.nu + self.ni, device=v.device).index_add(0, self.rows, v) + 1e-7
        return v * torch.pow(diags, -1)[self.rows]

    def propagate_on(self, adj, x):
        out = [x]
        for _ in range(self.layers):
            x = torch.sparse.mm(adj, x)
            out.append(x)
        x = torch.stack(out, dim=1).mean(1)
        return x[: self.nu], x[self.nu:]

    def forward(self, pruning=None):
        pruning = self.prune if pruning is None else pruning
        uf, itf = self.feats()
        vals = self.sim_values(uf, itf, pruning)
        self.adj_vals = vals.detach()
        adj = sparse_sorted(torch.stack([self.rows, self.cols]), vals, (self.nu + self.ni,) * 2)
        return self.propagate_on(adj, torch.cat([uf, itf]))

    def aug_adj(self, aug_user=None, aug_item=None, gen=None):
        """Authors' get_aug_adj on the detached denoised graph."""
        n = self.nu + self.ni
        nnz = len(self.adj_vals)
        if aug_user is None:
            pool = int(nnz * self.aug_ratio * 0.5 * 10)
            aug_user = torch.randint(0, self.nu, (pool,), device=self.dev, generator=gen)
            aug_item = torch.randint(0, self.ni, (pool,), device=self.dev, generator=gen)
        with torch.no_grad():
            uf, itf = self.feats()
            cos = (uf[aug_user] * itf[aug_item]).sum(1)
            _, idx = torch.topk(cos, int(nnz * self.aug_ratio * 0.5))
            au, ai = aug_user[idx], aug_item[idx]
            adj = torch.sparse_coo_tensor(torch.stack([self.rows, self.cols]), self.adj_vals, (n, n)).coalesce()
            val = torch.ones_like(au) * torch.median(adj.values())
            sub = torch.sparse_coo_tensor(torch.stack([au, ai + self.nu]), val, (n, n)).coalesce()
            aug = (adj + (sub + sub.t()).coalesce()).coalesce()
            r, c = aug.indices()
            d = torch.pow(torch.sparse.sum(aug, dim=1).to_dense() + 1e-7, -0.5)
            return torch.sparse_coo_tensor(aug.indices(), d[r] * aug.values() * d[r], (n, n)).coalesce()  # row degree on both sides, as the authors' lines do

    def ssl_forward(self, aug_user=None, aug_item=None, gen=None):
        uf, itf = self.feats()
        return self.propagate_on(self.aug_adj(aug_user, aug_item, gen), torch.cat([uf, itf]))

    @torch.no_grad()
    def propagate(self):
        return self.forward(self.prune)


def ssl_triple_loss(z1, z2, all_emb, tau):
    n1, n2, na = F.normalize(z1), F.normalize(z2), F.normalize(all_emb)
    pos = torch.exp(torch.mul(n1, n2).sum(dim=1) / tau)
    ttl = torch.exp(torch.matmul(n1, na.transpose(0, 1)) / tau).sum(dim=1)
    return -torch.log(pos / ttl).sum()


def rgcf_loss(model, u, p, n, reg_weight, mim_weight, aug_user=None, aug_item=None, gen=None):
    """Authors' RGCF.calculate_loss for one batch."""
    U, I = model.forward()
    eu, ep, en = U[u], I[p], I[n]
    pos, neg = (eu * ep).sum(1), (eu * en).sum(1)
    mf = -torch.log(1e-10 + torch.sigmoid(pos - neg)).mean()
    loss = mf
    if reg_weight > 0:
        uf, itf = model.feats()
        a, b, c = uf[u], itf[p], itf[n]
        reg = (torch.norm(a, p=2) + torch.norm(b, p=2) + torch.norm(c, p=2)) / c.shape[0]
        loss = loss + reg_weight * reg
    if mim_weight > 0:
        AU, _ = model.ssl_forward(aug_user, aug_item, gen)
        loss = loss + mim_weight * ssl_triple_loss(eu, AU[u], AU, model.tau)
    return loss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prune_threshold", type=float, default=0.02, help="beta: reliability below this is pruned (paper {0.02,...,0.1})")
    ap.add_argument("--MIM_weight", type=float, default=1e-6, help="lambda1: diversity loss weight (paper {1e-5,...,1e-8})")
    ap.add_argument("--tau", type=float, default=0.2, help="MIM temperature (paper {0.05, 0.1, 0.2})")
    ap.add_argument("--aug_ratio", type=float, default=0.1)
    ap.add_argument("--reg_weight", type=float, default=1e-5)
    ap.add_argument("--lr_mult", type=float, default=1.0, help="Adam learning rate = --lr x this")
    ap.add_argument("--reg", type=float, default=0.0, help="accepted for the pipeline; NOT used (see module doc)")
    ap.add_argument("--data", required=True)
    ap.add_argument("--train_file", default="train.tsv")
    ap.add_argument("--model", choices=["lightgcn"], default="lightgcn")
    ap.add_argument("--dim", type=int, default=64)
    ap.add_argument("--layers", type=int, default=3)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--batch", type=int, default=4096)
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
    users_all, items_all = train["user"].values, train["item"].values
    model = RGCF(nu, ni, users_all, items_all, a.dim, a.layers, a.prune_threshold, a.tau, a.aug_ratio, a.device).to(dev)
    lr_eff = a.lr * a.lr_mult
    opt = torch.optim.Adam(model.parameters(), lr=lr_eff)

    if dev.type == "cuda":
        torch.cuda.reset_peak_memory_stats(dev)
    t0 = time.time()
    best, best_epoch, bad = -1.0, 0, 0
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
            loss = rgcf_loss(model, u, p, n, a.reg_weight, a.MIM_weight, gen=gen)
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item() * len(idx)
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
        U, I = model.propagate()
        export_topk(lambda users: U[users] @ I.T, a.data, a.run_dir, a.train_file, device=dev)
    info = {**vars(a), "loss": "bpr+mim", "lr_effective": lr_eff, "best_valid_ndcg@20": best, "best_epoch": best_epoch,
            "epochs_run": epoch, "train_seconds": round(train_seconds, 1), "export_seconds": round(time.time() - t1, 1),
            "peak_gpu_mb": round(torch.cuda.max_memory_allocated(dev) / 2 ** 20) if dev.type == "cuda" else None}
    json.dump(info, open(os.path.join(a.run_dir, "run.json"), "w"), indent=2)
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
