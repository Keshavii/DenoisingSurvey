"""DrRL (Wang et al., Advancing Loss Functions in Recommender Systems: A Comparative Study with a Renyi
Divergence-Based Solution, AAAI 2025) on the kit's backbones: Part C adapter (code-change class 4).
Ported from the authors' code, github.com/cynthia-shengjia/AAAI-2025-DrRL @ faacdbc (optimizer/optim_DrRL.py DrRLOptimizer, model/model_MF.py
and model_LightGCN.py with norm_emb 1, tools/procedure.py Train).

What the authors' code does, and this port does the same:
  * Scores are cosine similarities: user and item embeddings are L2-normalised after the backbone (norm_emb 1).
  * Every training interaction (user, positive) is paired with 1024 negatives drawn uniformly, with replacement, from
    the items the user has not interacted with.
  * Every user has a learnable margin (initial value beta0, --renyi_margin), updated by plain SGD with learning
    rate lr2 (--lr2). With neg = the 1024 negative scores and omega* = omega / (omega - 1):
        search loss  = sum over rows of  neg^(-1/omega*) * || eps + relu(neg.detach() - margin) ||_omega*  + margin
        (backward on this loss moves only the margins)
        model loss   = mean over rows of relu(1 - pos) + neg^(-1/omega*) * || eps + relu(neg - margin.detach()) ||_omega*
                       + margin.detach()
    with eps = 0.1 and neg_coefficient 1 (code defaults).
  * --loss sl trains the authors' softmax loss instead (Plain-SL, the reference DrRL is compared with).
  * The embedding weight decay is 0 in all of the paper's settings (Table 8), so the kit's --reg is accepted but not
    used; --weight_decay (default 0) applies the authors' L2 term if wanted.

Kept from the kit, recorded as adaptations: the kit's Backbone (normal(0, 0.1) initialisation, 3 LightGCN layers),
Adam with learning rate lr * lr_mult, batch 2048 (authors: 1024), one pass over the training interactions per epoch
(as the authors), selection on clean-validation NDCG@20 every epoch with patience 20 (authors: every 5 epochs,
patience 5), seed, export. --lr_mult scales the plain model's learning rate (the pipeline passes --lr from the plain
model of the same backbone and dataset); the paper tunes the learning rate per setting (Table 8: 1e-5 to 1e-1).

  python -m rq1kit.drrl --renyi_omega 1.2 --renyi_margin 0.85 --lr_mult 10 --data data/yelp --model lightgcn \
      --lr 5e-3 --run_dir runs/yelp/drrl_lightgcn_N0_s1 --seed 1
"""
import argparse
import json
import math
import os
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .backbone import Backbone, norm_adj, valid_ndcg
from .data import load_split, to_csr
from .export import export_topk

EPS = 1e-1  # authors' self.eps


class NormBackbone(Backbone):
    """The kit's backbone with L2-normalised outputs (authors' norm_emb 1): scores are cosine similarities."""

    def propagate(self):
        u, i = super().propagate()
        return F.normalize(u, p=2, dim=1), F.normalize(i, p=2, dim=1)


class RenyiMargin:
    """Per-user margins and the DrRL loss (authors' DrRLOptimizer.cal_loss, same operations in the same order)."""

    def __init__(self, n_users, beta0, lr2, omega, n_neg, coef, device):
        self.margin = nn.Parameter(torch.full((n_users, 1), float(beta0), dtype=torch.float32, device=device))
        self.opt = torch.optim.SGD([self.margin], lr=lr2)
        self.omega_star = omega / (omega - 1)
        self.n_neg = n_neg
        self.coef = coef

    def loss(self, users, y_pred):
        m = self.margin[users]
        pos, neg = y_pred[:, 0], y_pred[:, 1:]
        const = math.pow(self.n_neg, -1 / self.omega_star)
        search = (const * torch.norm(EPS + torch.relu(neg.detach() - m) * self.coef, self.omega_star, dim=1)
                  + m.squeeze()).sum()
        self.opt.zero_grad()
        search.backward()
        self.opt.step()
        md = m.detach()
        neg_loss = const * torch.norm(EPS + torch.relu(neg - md) * self.coef, self.omega_star, dim=1) + md.squeeze()
        return (torch.relu(1 - pos) + neg_loss).mean()


def softmax_loss(y_pred, temp):
    """Authors' SoftmaxOptimizer.cal_loss (their 'softmax' loss, SL): the denominator sums the exponentials of the
    negative scores only, as in their code. Plain-SL in Part C is this loss with the same cosine scores, 1024
    negatives and sampler as DrRL, so DrRL's gain over it isolates the Renyi margin."""
    pos = torch.exp(y_pred[:, 0] / temp)
    neg = torch.exp(y_pred[:, 1:] / temp).sum(-1)
    return -torch.log(pos / neg).mean()


def sample_negatives_many(users, n_neg, n_items, keys, gen, tries=20):
    """n_neg items per user, uniform over the items the user has not interacted with, with replacement
    (authors: torch.multinomial over the user's non-interaction row). Uniform draws, redrawn where they hit a
    training item; keys = sorted user * n_items + item of the training interactions, on the same device."""
    neg = torch.randint(0, n_items, (len(users), n_neg), device=users.device, generator=gen)
    base = users.long()[:, None] * n_items
    for _ in range(tries):
        k = (base + neg).flatten()
        pos = torch.searchsorted(keys, k).clamp(max=len(keys) - 1)
        clash = (keys[pos] == k).view_as(neg)
        if not clash.any():
            break
        neg = torch.where(clash, torch.randint(0, n_items, neg.shape, device=users.device, generator=gen), neg)
    return neg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loss", choices=["drrl", "sl"], default="drrl", help="drrl, or sl = the authors' softmax loss (Plain-SL)")
    ap.add_argument("--ssm_temp", type=float, default=0.2, help="SL temperature tau (paper Table 8, SL: 0.07-0.26)")
    ap.add_argument("--renyi_omega", type=float, default=1.2, help="gamma: Renyi order (paper Table 8: 1.08-1.27)")
    ap.add_argument("--renyi_margin", type=float, default=0.85, help="beta0: initial margin (paper: 0.70-0.90)")
    ap.add_argument("--lr2", type=float, default=1e-4, help="margin learning rate (paper: 1e-5 or 1e-4)")
    ap.add_argument("--lr_mult", type=float, default=1.0, help="Adam learning rate = --lr x this")
    ap.add_argument("--num_negative_items", type=int, default=1024)
    ap.add_argument("--neg_coefficient", type=float, default=1.0)
    ap.add_argument("--weight_decay", type=float, default=0.0, help="authors' L2 term (0 in all paper settings)")
    ap.add_argument("--reg", type=float, default=0.0, help="accepted for the pipeline; NOT used (see module doc)")
    ap.add_argument("--data", required=True)
    ap.add_argument("--train_file", default="train.tsv")
    ap.add_argument("--model", choices=["mf", "lightgcn"], default="lightgcn")
    ap.add_argument("--dim", type=int, default=64)
    ap.add_argument("--layers", type=int, default=3)
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
    gen = torch.Generator(device=dev).manual_seed(a.seed)
    meta, train, valid_clean, valid_noisy, test = load_split(a.data, a.train_file)
    nu, ni = meta["n_users"], meta["n_items"]
    train = train.drop_duplicates(["user", "item"])
    train_csr = to_csr(train, nu, ni)
    truths = {"valid_clean": to_csr(valid_clean, nu, ni), "valid_noisy": to_csr(valid_noisy, nu, ni)}
    keys = torch.tensor(np.sort(train["user"].values.astype(np.int64) * ni + train["item"].values), device=dev)
    adj = norm_adj(train_csr, dev) if a.model == "lightgcn" else None
    model = NormBackbone(nu, ni, a.dim, a.model, a.layers, adj).to(dev)
    lr_eff = a.lr * a.lr_mult
    opt = torch.optim.Adam(model.parameters(), lr=lr_eff)
    drrl = RenyiMargin(nu, a.renyi_margin, a.lr2, a.renyi_omega, a.num_negative_items, a.neg_coefficient, dev)
    users_all, items_all = train["user"].values, train["item"].values

    if dev.type == "cuda":
        torch.cuda.reset_peak_memory_stats(dev)
    t0 = time.time()
    best, best_epoch, bad = -1.0, 0, 0
    hf = open(os.path.join(a.run_dir, "history.jsonl"), "w")
    for epoch in range(1, a.epochs + 1):
        model.train()
        perm = rng.permutation(len(users_all))
        tot = 0.0
        for s in range(0, len(perm), a.batch):
            idx = perm[s:s + a.batch]
            u = torch.tensor(users_all[idx], device=dev)
            p = torch.tensor(items_all[idx], device=dev)
            n = sample_negatives_many(u, a.num_negative_items, ni, keys, gen)
            U, I = model.propagate()
            eu, ep, en = U[u], I[p], I[n]
            y = torch.cat([(eu * ep).sum(1, keepdim=True), torch.bmm(eu.unsqueeze(1), en.transpose(1, 2)).squeeze(1)], 1)
            loss = drrl.loss(u, y) if a.loss == "drrl" else softmax_loss(y, a.ssm_temp)
            if a.weight_decay:
                reg = (model.user(u).pow(2).sum() + model.item(p).pow(2).sum() + model.item(n).pow(2).sum()) / 2
                loss = loss + a.weight_decay * reg / len(idx)
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
        with torch.no_grad():
            U, I = model.propagate()
        export_topk(lambda users: U[users] @ I.T, a.data, a.run_dir, a.train_file, device=dev)
    info = {**vars(a), "loss": a.loss, "lr_effective": lr_eff, "best_valid_ndcg@20": best, "best_epoch": best_epoch,
            "epochs_run": epoch, "train_seconds": round(train_seconds, 1), "export_seconds": round(time.time() - t1, 1),
            "peak_gpu_mb": round(torch.cuda.max_memory_allocated(dev) / 2 ** 20) if dev.type == "cuda" else None}
    json.dump(info, open(os.path.join(a.run_dir, "run.json"), "w"), indent=2)
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
