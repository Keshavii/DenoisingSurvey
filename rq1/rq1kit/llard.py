"""LLaRD (Wang et al., 2025; LLM-derived profile and relation knowledge for denoising) in the kit:
Part C adapter (code-change class 4), ML-1M only. Ported from the authors' code, github.com/shuyao-wang/LLaRD @ 936fe15
(LLaRD.py: LLaRD.graph_learner, forward, bpr_loss, hsic_graph, cal_infonce_loss, calculate_LLaRD_loss;
load_dataset.py: get_ui_matrix, get_uu_i_matrix, negative_sampling; run_LLaRD.py: parse_args, eval_test, the loop).

What the authors' code does, and this port does the same (model LGN, 3 layers, dim 64):
  * Four embedding tables (collaborative and "structure" tables for users and items, normal(0, 0.01)), a profile MLP over
    the LLM sentence embeddings of the user and item profiles, and an edge scorer MLP (2 dim -> dim -> 1).
  * Denoised graph, drawn anew in every batch: each edge of the symmetric-normalised training graph gets the gate
    sigmoid((logit + log eps - log(1 - eps)) / 0.2) + edge_bias, eps ~ U(0, 1); LightGCN propagation on it (mean over
    layers 0..3) gives the recommender's embeddings. The original graph's embeddings are also computed.
  * LLM knowledge as a second graph: the user-item graph after the LLM's deletion and addition of one item per user
    plus the user-user links the LLM chose (rel_k/aug_traindata.npy, rel_k/uu_data.npy), normalised like the first;
    a second LightGCN on the "structure" tables.
  * Loss = BPR(denoised embeddings) + l2_reg x ego-norm
           + alpha x ( prf_weight x InfoNCE(denoised vs MLP(profile embedding))
                      + str_weight x (BPR(structure embeddings) + l2_reg x ego-norm + 0.01 x InfoNCE(denoised vs structure)) )
           + beta x HSIC(original vs denoised embeddings of the batch's users and items)
    (InfoNCE: users against all profile embeddings, positive and negative items against the batch's own).
  * Evaluation embeddings: the denoised graph with a fresh random gate, as in run_LLaRD.eval_test.
  * Authors' defaults: lr 1e-3, batch 1024, l2_reg 1e-4, alpha 0.1, beta 5, sigma 0.25, prf_weight 0.01, str_weight 1,
    kd_temperature 0.2, edge_bias 0.5, 1000 epochs, stop after 10 epochs without improvement once past epoch 50.

The LLM knowledge (profile embeddings, deleted / added items, added users) is not shipped by the authors for the kit's
splits; rq1kit.llard_knowledge rebuilds it from the kit's own training file (see its documentation for the
adaptations: Llama-3.1-8B instead of Qwen-long, our own profile prompts, local sentence embeddings). One build per
training file: <data>/llard/N0 for train.tsv, <data>/llard/N2_20_s1 for train_N2_20_s1.tsv, ...

Kept from the kit, recorded as adaptations: selection of the epoch on clean-validation NDCG@20 every epoch (authors: NDCG@20
on the test file, which is also their validation file); the kit's batch construction (every training edge once per epoch with a
uniform negative; the authors' last batch re-uses edges); the sparse graph (the authors densify it); the pipeline's tuned
--lr scaled by --lr_mult; --reg accepted and NOT used (the authors fix l2_reg at 1e-4, --l2_reg sets it); seed; export.

  python -m rq1kit.llard --data data/ml1m --train_file train_N2_20_s1.tsv --lr 1e-3 --run_dir runs/ml1m/llard_N2_20_s1
"""
import argparse
import json
import os
import pickle
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .backbone import sample_negatives, valid_ndcg
from .data import load_split, to_csr
from .export import export_topk


def normalised_graph(rows, cols, n):
    """Authors' dense construction as a sparse tensor: duplicates add up, entries divided by sqrt(D_row) sqrt(D_col), D =
    row sums of the (possibly asymmetric) matrix, rows without entries have D = 1."""
    idx = torch.tensor(np.stack([rows, cols]), dtype=torch.long)
    g = torch.sparse_coo_tensor(idx, torch.ones(idx.shape[1]), (n, n)).coalesce()
    r, c = g.indices()
    deg = torch.zeros(n).index_add(0, r, g.values())
    deg[deg == 0.] = 1.
    return torch.sparse_coo_tensor(g.indices(), g.values() / (deg[r].sqrt() * deg[c].sqrt()), (n, n)).coalesce()


def kernel_matrix(x, sigma):
    return torch.exp((torch.matmul(x, x.transpose(0, 1)) - 1) / sigma)


def hsic(Kx, Ky, m):
    Kxy = torch.mm(Kx, Ky)
    h = torch.trace(Kxy) / m ** 2 + torch.mean(Kx) * torch.mean(Ky) - 2 * torch.mean(Kxy) / m
    return h * (m / (m - 1)) ** 2


def infonce(embeds1, embeds2, all_embeds2, temp=1.0):
    n1 = embeds1 / torch.sqrt(1e-8 + embeds1.square().sum(-1, keepdim=True))
    n2 = embeds2 / torch.sqrt(1e-8 + embeds2.square().sum(-1, keepdim=True))
    na = all_embeds2 / torch.sqrt(1e-8 + all_embeds2.square().sum(-1, keepdim=True))
    nume = -(n1 * n2 / temp).sum(-1)
    deno = torch.log(torch.sum(torch.exp(n1 @ na.T / temp), dim=-1))
    return (nume + deno).sum()


class LLaRDNet(nn.Module):
    def __init__(self, nu, ni, adj, aug_adj, user_prf, item_prf, dim=64, layers=3, l2_reg=1e-4, beta=5.0, alpha=0.1,
                 sigma=0.25, edge_bias=0.5, batch_size=1024, prf_weight=0.01, str_weight=1.0, kd_temperature=0.2):
        super().__init__()
        self.nu, self.ni, self.layers, self.dim = nu, ni, layers, dim
        self.l2_reg, self.beta, self.alpha, self.sigma, self.delta = l2_reg, beta, alpha, sigma, 0.01
        self.edge_bias, self.batch_size, self.prf_weight, self.str_weight = edge_bias, batch_size, prf_weight, str_weight
        self.kd_temperature = kd_temperature
        self.adj, self.aug_adj = adj, aug_adj
        self.register_buffer("user_prf", user_prf, persistent=False)
        self.register_buffer("item_prf", item_prf, persistent=False)
        self.mlp = nn.Sequential(nn.Linear(user_prf.shape[1], (user_prf.shape[1] + dim) // 2), nn.LeakyReLU(),
                                 nn.Linear((user_prf.shape[1] + dim) // 2, dim))
        self.user_embeddings = nn.Embedding(nu, dim)
        self.item_embeddings = nn.Embedding(ni, dim)
        self.user_str_embeddings = nn.Embedding(nu, dim)
        self.item_str_embeddings = nn.Embedding(ni, dim)
        for e in (self.user_embeddings, self.item_embeddings, self.user_str_embeddings, self.item_str_embeddings):
            nn.init.normal_(e.weight, std=0.01)
        self.activate = nn.ReLU()
        self.linear_1 = nn.Linear(2 * dim, dim, bias=True)
        self.linear_2 = nn.Linear(dim, 1, bias=True)
        for m in self.mlp:
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)

    def to(self, *a, **k):
        super().to(*a, **k)
        dev = next(self.parameters()).device
        self.adj, self.aug_adj = self.adj.to(dev), self.aug_adj.to(dev)
        return self

    def graph_learner(self, eps=None):
        all_emb = torch.cat([self.user_embeddings.weight, self.item_embeddings.weight], dim=0)
        row, col = self.adj.indices()
        logit = self.linear_2(self.activate(self.linear_1(torch.cat([all_emb[row], all_emb[col]], dim=1)))).view(-1)
        if eps is None:
            eps = torch.rand(logit.shape).to(logit.device)
        gate = torch.sigmoid((logit + torch.log(eps) - torch.log(1 - eps)) / 0.2) + self.edge_bias
        return torch.sparse_coo_tensor(self.adj.indices(), self.adj.values() * gate, self.adj.shape).coalesce()

    def forward(self, adj, g_type="cf"):
        ego = torch.cat([self.user_embeddings.weight, self.item_embeddings.weight] if g_type == "cf"
                        else [self.user_str_embeddings.weight, self.item_str_embeddings.weight], dim=0)
        out = [ego]
        for _ in range(self.layers):
            out.append(torch.sparse.mm(adj, out[-1]))
        mean = torch.mean(torch.stack(out, dim=1), dim=1)
        return mean[: self.nu], mean[self.nu:]

    def bpr(self, users, pos, neg, U, I, ego_u, ego_i):
        reg = 1 / 2 * (ego_u(users).norm(2).pow(2) + ego_i(pos).norm(2).pow(2) + ego_i(neg).norm(2).pow(2)) / float(len(users))
        pos_s, neg_s = torch.sum(U[users] * I[pos], dim=1), torch.sum(U[users] * I[neg], dim=1)
        auc = torch.mean((pos_s > neg_s).float())
        return auc, torch.mean(-torch.log(torch.sigmoid(pos_s - neg_s) + 1e-9)), reg * self.l2_reg

    def loss(self, users, pos, neg, eps=None):
        masked = self.graph_learner(eps)
        U_old, I_old = self.forward(self.adj, "cf")
        U, I = self.forward(masked, "cf")
        anc, pe, ne = U[users], I[pos], I[neg]
        user_prf, item_prf = self.mlp(self.user_prf), self.mlp(self.item_prf)
        ancp, posp, negp = user_prf[users], item_prf[pos], item_prf[neg]
        Us, Is = self.forward(self.aug_adj, "llm")
        ancs, poss, negs = Us[users], Is[pos], Is[neg]
        auc, bpr, reg = self.bpr(users, pos, neg, U, I, self.user_embeddings, self.item_embeddings)
        llm_auc, llm_bpr, llm_reg = self.bpr(users, pos, neg, Us, Is, self.user_str_embeddings, self.item_str_embeddings)
        prf = infonce(anc, ancp, user_prf, self.kd_temperature) + infonce(pe, posp, posp, self.kd_temperature) \
            + infonce(ne, negp, negp, self.kd_temperature)
        prf = prf / anc.shape[0] * self.prf_weight
        str_cl = infonce(anc, ancs, Us, self.kd_temperature) + infonce(pe, poss, poss, self.kd_temperature) \
            + infonce(ne, negs, negs, self.kd_temperature)
        str_loss = ((llm_bpr + llm_reg) + str_cl / anc.shape[0] * self.delta) * self.str_weight
        # minimum mutual information between the original and the denoised representation
        u_unique, i_unique = torch.unique(users), torch.unique(pos)
        ux, uy = F.normalize(U_old[u_unique], p=2, dim=1), F.normalize(U[u_unique], p=2, dim=1)
        ix, iy = F.normalize(I_old[i_unique], p=2, dim=1), F.normalize(I[i_unique], p=2, dim=1)
        ib = (hsic(kernel_matrix(ux, self.sigma), kernel_matrix(uy, self.sigma), self.batch_size)
              + hsic(kernel_matrix(ix, self.sigma), kernel_matrix(iy, self.sigma), self.batch_size)) * self.beta
        total = bpr + reg + (prf + str_loss) * self.alpha + ib
        return total, dict(bpr=bpr.item(), prf=prf.item(), str=str_loss.item(), ib=ib.item())

    @torch.no_grad()
    def propagate(self):
        """Authors' eval_test: the denoised graph with a fresh random gate."""
        return self.forward(self.graph_learner(), "cf")


def build_graphs(nu, ni, train_users, train_items, aug, uu, device):
    n = nu + ni
    rows = np.concatenate([train_users, train_items + nu])
    cols = np.concatenate([train_items + nu, train_users])
    adj = normalised_graph(rows, cols, n)
    au = np.array([u for u, its in aug.items() for _ in its], dtype=np.int64)
    ai = np.array([i for its in aug.values() for i in its], dtype=np.int64)
    su = np.array([u for u, vs in uu.items() for _ in vs], dtype=np.int64)
    sv = np.array([v for vs in uu.values() for v in vs], dtype=np.int64)
    aug_rows = np.concatenate([au, ai + nu, su])  # the authors add the user-user links in one direction only
    aug_cols = np.concatenate([ai + nu, au, sv])
    return adj, normalised_graph(aug_rows, aug_cols, n)


def build_name(train_file):
    stem = os.path.splitext(train_file)[0]
    return "N0" if stem == "train" else stem[len("train_"):]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", type=float, default=0.1, help="weight of the LLM losses (authors 0.1)")
    ap.add_argument("--beta", type=float, default=5.0, help="weight of the HSIC term (authors 5.0)")
    ap.add_argument("--sigma", type=float, default=0.25)
    ap.add_argument("--prf_weight", type=float, default=0.01)
    ap.add_argument("--str_weight", type=float, default=1.0)
    ap.add_argument("--kd_temperature", type=float, default=0.2)
    ap.add_argument("--edge_bias", type=float, default=0.5)
    ap.add_argument("--l2_reg", type=float, default=1e-4)
    ap.add_argument("--lr_mult", type=float, default=1.0, help="Adam learning rate = --lr x this")
    ap.add_argument("--reg", type=float, default=0.0, help="accepted for the pipeline; NOT used (see module doc)")
    ap.add_argument("--knowledge_dir", default="", help="default: <data>/llard")
    ap.add_argument("--data", required=True)
    ap.add_argument("--train_file", default="train.tsv")
    ap.add_argument("--model", choices=["lightgcn"], default="lightgcn")
    ap.add_argument("--dim", type=int, default=64)
    ap.add_argument("--layers", type=int, default=3)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--batch", type=int, default=1024)
    ap.add_argument("--epochs", type=int, default=1000)
    ap.add_argument("--min_epochs", type=int, default=50, help="authors: early stopping only after epoch 50")
    ap.add_argument("--patience", type=int, default=10)
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
    kdir = os.path.join(a.knowledge_dir or os.path.join(a.data, "llard"), build_name(a.train_file))
    need = [os.path.join(kdir, p) for p in ("prf_k/usr_emb_np.pkl", "prf_k/itm_emb_np.pkl", "rel_k/aug_traindata.npy", "rel_k/uu_data.npy")]
    missing = [p for p in need if not os.path.isfile(p)]
    if missing:
        raise SystemExit(f"LLM knowledge for {a.train_file} is missing: {missing}. Build it with rq1kit.llard_knowledge "
                         f"(--build {build_name(a.train_file)}) or copy <data>/llard from the machine that has it.")
    user_prf = torch.tensor(pickle.load(open(need[0], "rb"))).float()
    item_prf = torch.tensor(pickle.load(open(need[1], "rb"))).float()
    aug = np.load(need[2], allow_pickle=True).tolist()
    uu = np.load(need[3], allow_pickle=True).tolist()
    users_all, items_all = train["user"].values.astype(np.int64), train["item"].values.astype(np.int64)
    adj, aug_adj = build_graphs(nu, ni, users_all, items_all, aug, uu, dev)
    model = LLaRDNet(nu, ni, adj, aug_adj, user_prf, item_prf, a.dim, a.layers, a.l2_reg, a.beta, a.alpha, a.sigma,
                     a.edge_bias, a.batch, a.prf_weight, a.str_weight, a.kd_temperature).to(dev)
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
            if len(idx) < 2:
                continue
            u = torch.tensor(users_all[idx], device=dev)
            p = torch.tensor(items_all[idx], device=dev)
            n = torch.tensor(neg_all[s:s + a.batch], device=dev)
            loss, _ = model.loss(u, p, n)
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
            if bad >= a.patience and epoch > a.min_epochs:
                break
    train_seconds = time.time() - t0
    model.load_state_dict(torch.load(os.path.join(a.run_dir, "best.pt"), map_location=dev, weights_only=True))
    model.eval()
    t1 = time.time()
    if not a.no_export:
        U, I = model.propagate()
        export_topk(lambda users: U[users] @ I.T, a.data, a.run_dir, a.train_file, device=dev)
    info = {**vars(a), "loss": "llard", "lr_effective": lr_eff, "knowledge_dir": kdir, "best_valid_ndcg@20": best,
            "best_epoch": best_epoch, "epochs_run": epoch, "train_seconds": round(train_seconds, 1),
            "export_seconds": round(time.time() - t1, 1),
            "peak_gpu_mb": round(torch.cuda.max_memory_allocated(dev) / 2 ** 20) if dev.type == "cuda" else None}
    json.dump(info, open(os.path.join(a.run_dir, "run.json"), "w"), indent=2)
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
