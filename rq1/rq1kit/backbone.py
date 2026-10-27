"""Plain backbones (MF-BPR and LightGCN) trained the kit's way: the reference every RQ1 gain is measured from.

Also used for the oracle (train on train_clean.tsv) and as the sparse LightGCN for methods whose own LightGCN
does not fit one GPU (PLD builds a dense adjacency).

  python -m rq1kit.backbone --data data/yelp --model lightgcn --loss bpr --train_file train.tsv \
      --run_dir runs/yelp/plain_lightgcn_bpr_N0_s1 --seed 1

Model selection is on validation NDCG@20 (clean validation by default; --select valid_noisy for RQ2). Both
validation scores are logged every evaluation. The test set is touched once, at the end, through export_topk.
Outputs in run_dir: best.pt, topk_valid.npy, topk_test.npy, history.jsonl, run.json (settings, best epoch, cost).
"""
import argparse
import json
import os
import time

import numpy as np
import torch
import torch.nn as nn

from .data import load_split, to_csr
from .export import export_topk


class Backbone(nn.Module):
    def __init__(self, n_users, n_items, dim, model, layers, adj=None):
        super().__init__()
        self.nu, self.ni, self.model, self.layers = n_users, n_items, model, layers
        self.user = nn.Embedding(n_users, dim)
        self.item = nn.Embedding(n_items, dim)
        nn.init.normal_(self.user.weight, std=0.1)
        nn.init.normal_(self.item.weight, std=0.1)
        self.adj = adj

    def propagate(self):
        ego = torch.cat([self.user.weight, self.item.weight])
        if self.model == "mf":
            return self.user.weight, self.item.weight
        out, x = [ego], ego
        for _ in range(self.layers):
            x = torch.sparse.mm(self.adj, x)
            out.append(x)
        x = torch.stack(out).mean(0)
        return x[: self.nu], x[self.nu:]


def norm_adj(train_csr, device):
    nu, ni = train_csr.shape
    coo = train_csr.tocoo()
    r = np.concatenate([coo.row, coo.col + nu])
    c = np.concatenate([coo.col + nu, coo.row])
    deg = np.bincount(r, minlength=nu + ni).astype(np.float32)
    w = 1.0 / np.sqrt(deg[r] * deg[c])
    idx = torch.tensor(np.stack([r, c]), dtype=torch.long)
    return torch.sparse_coo_tensor(idx, torch.tensor(w, dtype=torch.float32), (nu + ni, nu + ni)).coalesce().to(device)


def sample_negatives(users, n_items, keys, rng, tries=10):
    neg = rng.integers(0, n_items, size=len(users))
    for _ in range(tries):
        k = users.astype(np.int64) * n_items + neg
        pos = np.searchsorted(keys, k)
        clash = (pos < len(keys)) & (keys[np.minimum(pos, len(keys) - 1)] == k)
        if not clash.any():
            break
        neg[clash] = rng.integers(0, n_items, size=int(clash.sum()))
    return neg


@torch.no_grad()
def valid_ndcg(model, train_csr, truth_csrs, device, batch=1024, k=20):
    U, I = model.propagate()
    disc = 1.0 / torch.log2(torch.arange(2, k + 2, device=device).float())
    res = {name: [] for name in truth_csrs}
    for s in range(0, model.nu, batch):
        rows = slice(s, min(s + batch, model.nu))
        scores = U[rows] @ I.T
        mask = torch.tensor(train_csr[rows].toarray(), device=device, dtype=torch.bool)
        top = torch.topk(scores.masked_fill(mask, float("-inf")), k, dim=1).indices
        for name, tc in truth_csrs.items():
            t = torch.tensor(tc[rows].toarray(), device=device, dtype=torch.bool)
            n_true = t.sum(1)
            keep = n_true > 0
            if keep.sum() == 0:
                continue
            hit = torch.gather(t, 1, top).float()
            dcg = (hit * disc).sum(1)
            idcg = torch.cumsum(disc, 0)[torch.clamp(n_true, max=k) - 1]
            res[name].append((dcg[keep] / idcg[keep]).cpu())
    return {n: float(torch.cat(v).mean()) if v else 0.0 for n, v in res.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--train_file", default="train.tsv")
    ap.add_argument("--model", choices=["mf", "lightgcn"], default="lightgcn")
    ap.add_argument("--loss", choices=["bpr", "bce"], default="bpr")
    ap.add_argument("--dim", type=int, default=64)
    ap.add_argument("--layers", type=int, default=3)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--reg", type=float, default=1e-4)
    ap.add_argument("--batch", type=int, default=2048)
    ap.add_argument("--epochs", type=int, default=300)
    ap.add_argument("--patience", type=int, default=20, help="evaluations without improvement before stopping")
    ap.add_argument("--eval_every", type=int, default=1)
    ap.add_argument("--select", choices=["valid_clean", "valid_noisy"], default="valid_clean")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--run_dir", required=True)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--no_export", action="store_true", help="tuning trials: skip the top-K export")
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

    if dev.type == "cuda":
        torch.cuda.reset_peak_memory_stats(dev)
    t0 = time.time()
    best, best_epoch, bad, hist = -1.0, 0, 0, []
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
            if a.loss == "bpr":
                loss = -torch.nn.functional.logsigmoid(pos - negs).mean()
            else:
                loss = -(torch.nn.functional.logsigmoid(pos) + torch.nn.functional.logsigmoid(-negs)).mean()
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
        rec = {"epoch": epoch, "loss": tot / len(perm), "seconds": round(time.time() - t0, 1), **{f"{k}_ndcg@20": x for k, x in v.items()}}
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
    info = {**vars(a), "best_valid_ndcg@20": best, "best_epoch": best_epoch, "epochs_run": epoch,
            "train_seconds": round(train_seconds, 1), "export_seconds": round(time.time() - t1, 1),
            "peak_gpu_mb": round(torch.cuda.max_memory_allocated(dev) / 2 ** 20) if dev.type == "cuda" else None}
    json.dump(info, open(os.path.join(a.run_dir, "run.json"), "w"), indent=2)
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
