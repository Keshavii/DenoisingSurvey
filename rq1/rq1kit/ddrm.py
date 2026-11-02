"""DDRM (Zhao et al., Denoising Diffusion Recommender Model, SIGIR 2024) on the kit's LightGCN: Part C adapter
(code-change class 4). Ported from the authors' code, github.com/Polaris-JZ/DDRM @ ad4034c
(DDRM_LightGCN/main.py, utils.py: BPRLoss.call_bpr; model.py: LightGCN.computer, computer_infer, bpr_loss, DNN;
diffusion.py; train.py, train_yelp.py, train_amazon.py).

DDRM is a plug-in on top of a trained recommender: the LightGCN is pretrained and then frozen (main.py sets
requires_grad = False for its parameters), and two conditional diffusion networks are trained on its embeddings.

What the authors' code does, and this port does the same:
  * Per batch (user, positive, negative), with frozen propagated embeddings u, p (and the negative's embedding n):
    noise is added to u and p at a random time step t, and two DNNs reconstruct them:
        u_hat = DNN_user(noisy u, p, t)        p_hat = DNN_item(noisy p, u, t)       (the other side is the condition)
        recon = (mean (u - u_hat)^2 + mean (p - p_hat)^2) / 2
        rec   = softplus(u_hat . n - u_hat . p_hat) + decay x |ego embeddings|^2 / 2 (constant, the LightGCN is frozen)
        loss  = mean( ((1 - alpha) rec + alpha recon) x sigmoid(pos score)^beta )        (beta 0 = no weighting)
    Only the two DNNs are updated (Adam, diff_lr).
  * Inference: for each user, the mean of the propagated embeddings of the user's training items is noised to the last
    diffusion step and denoised by DNN_item, conditioned on the user's embedding, for sampling_steps reverse steps (the
    authors use int(1.25 x steps) > steps; time steps beyond the schedule reuse its last value); the generated vector is
    scored against all item embeddings by inner product.
  * The training pairs of an epoch: a user drawn uniformly, one of its positives drawn uniformly, a uniform negative.
  * Authors' settings: DNN dims [200, 1000 or 1100], ReLU, time embedding 10, 50 steps, noise scale 1e-2 on
    [1e-4, 1e-3] (linear-var), alpha 0.1 (ML-1M) or 0.5 (Amazon-Book), beta 0, diff_lr 1e-3, batch 2048.

Kept from the kit, recorded as adaptations: the pretrained recommender is the kit's plain LightGCN-BPR trained on the same
training file with the pipeline's tuned --lr and --reg (python -m rq1kit.backbone, 3 layers, up to 300 epochs, patience 20;
authors: a checkpoint of their own LightGCN, 2 layers), cached under runs/_ddrm_pretrain so that tuning trials and reruns
reuse it; selection of the epoch of the DNNs on clean-validation NDCG@20 every 5 epochs with patience 6 evaluations
(authors: validation recall@10, patience 6 evaluations after epoch 30); seed; the kit's top-K export. The inference noise
is random (as theirs), seeded.

  python -m rq1kit.ddrm --diff_lr 1e-3 --alpha 0.1 --steps 50 --data data/yelp --lr 1e-3 --reg 1e-4 \
      --run_dir runs/yelp/ddrm_lightgcn_N0_s1 --seed 1
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from . import diffrec as D
from .backbone import Backbone, norm_adj, sample_negatives
from .data import load_split, to_csr
from .dense import valid_ndcg_scores
from .export import export_topk


class CondDNN(nn.Module):
    """Authors' model.DNN (DDRM_LightGCN): the noisy embedding, the time embedding and the condition are concatenated."""

    def __init__(self, in_dims, out_dims, emb_size, act="relu", norm=False, dropout=0.5):
        super().__init__()
        self.in_dims, self.out_dims, self.time_emb_dim, self.norm, self.act = in_dims, out_dims, emb_size, norm, act
        assert out_dims[0] == in_dims[-1], "In and out dimensions must equal to each other."
        self.emb_layer = nn.Linear(self.time_emb_dim, self.time_emb_dim)
        in_dims_temp = [self.in_dims[0] * 2 + self.time_emb_dim] + self.in_dims[1:]
        self.in_layers = nn.ModuleList([nn.Linear(a, b) for a, b in zip(in_dims_temp[:-1], in_dims_temp[1:])])
        self.out_layers = nn.ModuleList([nn.Linear(a, b) for a, b in zip(out_dims[:-1], out_dims[1:])])
        self.drop = nn.Dropout(dropout)
        for layer in list(self.in_layers) + list(self.out_layers) + [self.emb_layer]:
            size = layer.weight.size()
            layer.weight.data.normal_(0.0, np.sqrt(2.0 / (size[1] + size[0])))
            layer.bias.data.normal_(0.0, 0.001)

    def _act(self, x):
        return torch.tanh(x) if self.act == "tanh" else torch.sigmoid(x) if self.act == "sigmoid" else F.relu(x)

    def forward(self, noise_emb, con_emb, timesteps):
        emb = self.emb_layer(D.timestep_embedding(timesteps, self.time_emb_dim).to(noise_emb.device))
        if self.norm:
            noise_emb = F.normalize(noise_emb)
        h = torch.cat([self.drop(noise_emb), emb, con_emb], dim=-1)
        for layer in self.in_layers:
            h = self._act(layer(h))
        for i, layer in enumerate(self.out_layers):
            h = layer(h)
            if i != len(self.out_layers) - 1:
                h = self._act(h)
        return h


class CondDiffusion(D.GaussianDiffusion):
    """Authors' DDRM diffusion.py: the conditional p_mean_variance and the extraction that clamps to the last step."""

    def sample_timesteps_uniform(self, batch_size, device):
        return torch.randint(0, self.steps, (batch_size,), device=device).long()

    def p_mean_variance(self, model, x, con_emb, t):
        assert t.shape == (x.shape[0],)
        model_output = model(x, con_emb, t)
        model_variance = self._extract_into_tensor(self.posterior_variance, t, x.shape)
        model_log_variance = self._extract_into_tensor(self.posterior_log_variance_clipped, t, x.shape)
        if self.mean_type == D.ModelMeanType.START_X:
            pred_xstart = model_output
        else:
            pred_xstart = self._predict_xstart_from_eps(x, t, eps=model_output)
        model_mean, _, _ = self.q_posterior_mean_variance(x_start=pred_xstart, x_t=x, t=t)
        return {"mean": model_mean, "variance": model_variance, "log_variance": model_log_variance, "pred_xstart": pred_xstart}

    def _extract_into_tensor(self, arr, timesteps, broadcast_shape):
        arr = arr.to(timesteps.device)
        res = arr[-1].float() if timesteps[0] >= len(arr) else arr[timesteps].float()
        while len(res.shape) < len(broadcast_shape):
            res = res[..., None]
        return res.expand(broadcast_shape)


def ddrm_loss(U, I, ego_u, ego_p, ego_n, u, p, n, user_rev, item_rev, diff, alpha, beta, decay):
    """Authors' BPRLoss.call_bpr + LightGCN.computer + bpr_loss for one batch (frozen propagated embeddings U, I)."""
    ori_u, ori_p = U[u], I[p]
    ts = diff.sample_timesteps_uniform(ori_u.shape[0], ori_u.device)
    user_noise, item_noise = torch.randn_like(ori_u), torch.randn_like(ori_p)
    noisy_u, noisy_p = diff.q_sample(ori_u, ts, user_noise), diff.q_sample(ori_p, ts, item_noise)
    u_hat = user_rev(noisy_u, ori_p, ts)
    p_hat = item_rev(noisy_p, ori_u, ts)
    recon = (((ori_u - u_hat) ** 2).mean(dim=1) + ((ori_p - p_hat) ** 2).mean(dim=1)) / 2
    reg = (1 / 2) * (ego_u.norm(2).pow(2) + ego_p.norm(2).pow(2) + ego_n.norm(2).pow(2)) / float(len(u))
    pos_scores = torch.sum(u_hat * p_hat, dim=1)
    neg_scores = torch.sum(u_hat * I[n], dim=1)
    rec = F.softplus(neg_scores - pos_scores) + reg * decay
    weight = torch.pow(torch.sigmoid(pos_scores).detach(), beta)
    return ((1 - alpha) * rec + alpha * recon).mul(weight).mean()


@torch.no_grad()
def ddrm_scores(U, I, users, train_csr, item_rev, diff, sampling_steps, device):
    """Authors' LightGCN.computer_infer + rounding_inner for a batch of users."""
    cnt = np.asarray(train_csr[users.cpu().numpy()].sum(1)).reshape(-1).clip(min=1)
    rows = train_csr[users.cpu().numpy()].tocoo()
    m = torch.sparse_coo_tensor(np.stack([rows.row, rows.col]), np.ones(len(rows.row), dtype=np.float32),
                                (len(users), I.shape[0])).to(device)
    aver = torch.sparse.mm(m, I) / torch.tensor(cnt, device=device, dtype=torch.float32)[:, None]
    user_emb = U[users]
    t_last = torch.tensor([diff.steps - 1] * aver.shape[0]).to(device)
    x = diff.q_sample(aver, t_last, torch.randn_like(aver))
    for i in list(range(sampling_steps))[::-1]:
        t = torch.tensor([i] * x.shape[0]).to(device)
        x = diff.p_mean_variance(item_rev, x, user_emb, t)["mean"]
    return x @ I.T


def pretrained_lightgcn(a, dev):
    """The kit's plain LightGCN-BPR for this training file, trained once and cached."""
    key = hashlib.md5(json.dumps([a.data, a.train_file, a.seed, a.dim, a.layers, a.lr, a.reg, a.pre_epochs, a.pre_patience]).encode()).hexdigest()[:10]
    root = "runs/_ddrm_pretrain"
    cache = os.path.join(root, f"{os.path.basename(os.path.normpath(a.data))}_{os.path.splitext(a.train_file)[0]}_s{a.seed}_{key}")
    if not os.path.isfile(os.path.join(cache, "run.json")):
        tmp = f"{cache}.tmp{os.getpid()}"
        shutil.rmtree(tmp, ignore_errors=True)
        cmd = [sys.executable, "-m", "rq1kit.backbone", "--data", a.data, "--train_file", a.train_file, "--model", "lightgcn",
               "--loss", "bpr", "--dim", str(a.dim), "--layers", str(a.layers), "--lr", str(a.lr), "--reg", str(a.reg),
               "--epochs", str(a.pre_epochs), "--patience", str(a.pre_patience), "--seed", str(a.seed), "--no_export",
               "--device", a.device, "--run_dir", tmp]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
        os.makedirs(root, exist_ok=True)
        try:
            os.rename(tmp, cache)
        except OSError:  # another job finished the same pretraining first
            shutil.rmtree(tmp, ignore_errors=True)
    return os.path.join(cache, "best.pt"), cache


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diff_lr", type=float, default=1e-3, help="Adam learning rate of the two DNNs (authors 1e-3)")
    ap.add_argument("--alpha", type=float, default=0.1, help="weight of the reconstruction loss (authors 0.1 / 0.5)")
    ap.add_argument("--beta", type=float, default=0.0, help="exponent of the positive-score weight (authors 0)")
    ap.add_argument("--steps", type=int, default=50, help="diffusion steps (authors 50)")
    ap.add_argument("--sample_mult", type=float, default=1.25, help="sampling_steps = int(steps x this) (authors 1.25)")
    ap.add_argument("--noise_scale", type=float, default=1e-2)
    ap.add_argument("--noise_min", type=float, default=1e-4)
    ap.add_argument("--noise_max", type=float, default=1e-3)
    ap.add_argument("--noise_schedule", default="linear-var")
    ap.add_argument("--mean_type", choices=["x0", "eps"], default="x0")
    ap.add_argument("--dnn_dims", default="[200,1000]")
    ap.add_argument("--emb_size", type=int, default=10)
    ap.add_argument("--act", default="relu")
    ap.add_argument("--decay", type=float, default=0.0, help="authors' wd 0 in train*.py is not passed; their default 1e-4 acts on a constant")
    ap.add_argument("--pre_epochs", type=int, default=300)
    ap.add_argument("--pre_patience", type=int, default=20)
    ap.add_argument("--lr", type=float, default=1e-3, help="the pretrained LightGCN's learning rate (pipeline)")
    ap.add_argument("--reg", type=float, default=1e-4, help="the pretrained LightGCN's regularisation (pipeline)")
    ap.add_argument("--data", required=True)
    ap.add_argument("--train_file", default="train.tsv")
    ap.add_argument("--model", choices=["lightgcn"], default="lightgcn")
    ap.add_argument("--dim", type=int, default=64)
    ap.add_argument("--layers", type=int, default=3)
    ap.add_argument("--batch", type=int, default=2048)
    ap.add_argument("--epochs", type=int, default=1000)
    ap.add_argument("--patience", type=int, default=6)
    ap.add_argument("--eval_every", type=int, default=5)
    ap.add_argument("--select", choices=["valid_clean", "valid_noisy"], default="valid_clean")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--run_dir", required=True)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--no_export", action="store_true")
    a = ap.parse_args()

    os.makedirs(a.run_dir, exist_ok=True)
    pre_path, pre_dir = pretrained_lightgcn(a, None)
    torch.manual_seed(a.seed)
    np.random.seed(a.seed)
    rng = np.random.default_rng(a.seed)
    dev = torch.device(a.device)
    meta, train, valid_clean, valid_noisy, test = load_split(a.data, a.train_file)
    nu, ni = meta["n_users"], meta["n_items"]
    train = train.drop_duplicates(["user", "item"])
    train_csr = to_csr(train, nu, ni).tocsr()
    truths = {"valid_clean": to_csr(valid_clean, nu, ni), "valid_noisy": to_csr(valid_noisy, nu, ni)}
    keys = np.sort(train["user"].values.astype(np.int64) * ni + train["item"].values)
    rec = Backbone(nu, ni, a.dim, "lightgcn", a.layers, norm_adj(train_csr, dev)).to(dev)
    rec.load_state_dict(torch.load(pre_path, map_location=dev, weights_only=True))
    for q in rec.parameters():
        q.requires_grad = False
    with torch.no_grad():
        U, I = rec.propagate()

    mean_type = D.ModelMeanType.START_X if a.mean_type == "x0" else D.ModelMeanType.EPSILON
    diff = CondDiffusion(mean_type, a.noise_schedule, a.noise_scale, a.noise_min, a.noise_max, a.steps, dev)
    out_dims = eval(a.dnn_dims) + [a.dim]
    in_dims = out_dims[::-1]
    user_rev = CondDNN(in_dims, out_dims, a.emb_size, a.act).to(dev)
    item_rev = CondDNN(in_dims, out_dims, a.emb_size, a.act).to(dev)
    opt_u = torch.optim.Adam(user_rev.parameters(), lr=a.diff_lr)
    opt_i = torch.optim.Adam(item_rev.parameters(), lr=a.diff_lr)
    sampling_steps = int(a.steps * a.sample_mult)
    deg = np.diff(train_csr.indptr)
    n_pos = int(deg.sum())

    def score_fn(users):
        return ddrm_scores(U, I, users, train_csr, item_rev, diff, sampling_steps, dev)

    if dev.type == "cuda":
        torch.cuda.reset_peak_memory_stats(dev)
    t0 = time.time()
    best, best_epoch, bad = -1.0, 0, 0
    hf = open(os.path.join(a.run_dir, "history.jsonl"), "w")
    for epoch in range(1, a.epochs + 1):
        user_rev.train(); item_rev.train()
        users_e = rng.integers(0, nu, n_pos)
        users_e = users_e[deg[users_e] > 0]
        pos_e = train_csr.indices[train_csr.indptr[users_e] + (rng.random(len(users_e)) * deg[users_e]).astype(np.int64)]
        neg_e = sample_negatives(users_e, ni, keys, rng)
        tot = 0.0
        for s in range(0, len(users_e), a.batch):
            u = torch.tensor(users_e[s:s + a.batch], device=dev)
            p = torch.tensor(pos_e[s:s + a.batch], device=dev)
            n = torch.tensor(neg_e[s:s + a.batch], device=dev)
            loss = ddrm_loss(U, I, rec.user(u), rec.item(p), rec.item(n), u, p, n, user_rev, item_rev, diff,
                             a.alpha, a.beta, a.decay)
            opt_u.zero_grad(); opt_i.zero_grad()
            loss.backward()
            opt_i.step(); opt_u.step()
            tot += loss.item() * len(u)
        if epoch % a.eval_every:
            continue
        user_rev.eval(); item_rev.eval()
        v = valid_ndcg_scores(score_fn, nu, train_csr, truths, dev)
        r = {"epoch": epoch, "loss": tot / max(len(users_e), 1), "seconds": round(time.time() - t0, 1),
             **{f"{k}_ndcg@20": x for k, x in v.items()}}
        hf.write(json.dumps(r) + "\n"); hf.flush()
        print(r, flush=True)
        if v[a.select] > best:
            best, best_epoch, bad = v[a.select], epoch, 0
            torch.save({"user": user_rev.state_dict(), "item": item_rev.state_dict()}, os.path.join(a.run_dir, "best.pt"))
        else:
            bad += 1
            if bad >= a.patience:
                break
    train_seconds = time.time() - t0
    sd = torch.load(os.path.join(a.run_dir, "best.pt"), map_location=dev, weights_only=True)
    user_rev.load_state_dict(sd["user"]); item_rev.load_state_dict(sd["item"])
    user_rev.eval(); item_rev.eval()
    t1 = time.time()
    if not a.no_export:
        export_topk(score_fn, a.data, a.run_dir, a.train_file, device=dev)
    info = {**vars(a), "loss": "ddrm", "pretrain_dir": pre_dir, "sampling_steps": sampling_steps,
            "best_valid_ndcg@20": best, "best_epoch": best_epoch, "epochs_run": epoch,
            "train_seconds": round(train_seconds, 1), "export_seconds": round(time.time() - t1, 1),
            "peak_gpu_mb": round(torch.cuda.max_memory_allocated(dev) / 2 ** 20) if dev.type == "cuda" else None}
    json.dump(info, open(os.path.join(a.run_dir, "run.json"), "w"), indent=2)
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
