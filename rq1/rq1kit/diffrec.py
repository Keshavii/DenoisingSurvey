"""DiffRec (Wang et al., Diffusion Recommender Model, SIGIR 2023) in the kit: Part C adapter (code-change class 4).
Ported from the authors' code, github.com/YiyanXu/DiffRec @ e42532f (DiffRec/main.py, models/DNN.py,
models/gaussian_diffusion.py). DiffRec is the plain variant (not L-, T- or LT-DiffRec), as in Part B.

What the authors' code does, and this port does the same:
  * The model denoises a user's whole interaction row x0 (n_items values, 0/1): the forward process adds Gaussian noise
    with a linear-variance schedule over `steps` steps; an MLP (DNN: time embedding concatenated to the input, tanh
    layers, dropout 0.5 on the input) predicts x0 from x_t; loss = importance-sampled (after the first 10 losses of every
    step), SNR-reweighted MSE.
  * Inference: the user's training row is the input, p_sample runs the reverse chain from sampling_steps (0 = from the
    row itself, no noise added) and returns a score for every item; items in the user's training row are masked.
  * Authors' optimiser AdamW, batch 400, dims [1000], time embedding 10, mean type x0, 1000 epochs, evaluation every 5
    epochs, stop after 20 epochs (4 evaluations) without improvement.
The two model classes (DNN, GaussianDiffusion) are the authors' code; the only differences are in how the loss history
of the importance sampler is stored (numpy on the CPU instead of one GPU element write per sample, same arithmetic,
checked against their code in tests/test_diffrec.py) and the per-batch construction of the dense rows (see below).

Kept from the kit, recorded as adaptations: the user rows are built batch by batch from the sparse training matrix (the
authors hold the dense users x items matrix, 19 GB on Amazon-Book, 47 GB peak in Part B); selection of the epoch on
clean-validation NDCG@20 (authors: recall@20 on the validation set), the kit's data split and seeds, the kit's top-K export.
DiffRec has no embedding table and no LightGCN: the pipeline's --model, --lr and --reg are accepted and NOT used; the
learning rate is tuned here as --diff_lr. Only the LightGCN conditions are scheduled for it.

  python -m rq1kit.diffrec --diff_lr 1e-4 --noise_scale 1e-3 --steps 5 --data data/yelp \
      --run_dir runs/yelp/diffrec_N0_s1 --seed 1
"""
import argparse
import enum
import json
import math
import os
import time

import numpy as np
import torch
import torch as th
import torch.nn as nn
import torch.nn.functional as F

from .data import load_split, to_csr
from .dense import valid_ndcg_scores
from .export import export_topk


class ModelMeanType(enum.Enum):
    START_X = enum.auto()
    EPSILON = enum.auto()


def timestep_embedding(timesteps, dim, max_period=10000):
    half = dim // 2
    freqs = torch.exp(-math.log(max_period) * torch.arange(start=0, end=half, dtype=torch.float32) / half).to(timesteps.device)
    args = timesteps[:, None].float() * freqs[None]
    embedding = torch.cat([torch.cos(args), torch.sin(args)], dim=-1)
    if dim % 2:
        embedding = torch.cat([embedding, torch.zeros_like(embedding[:, :1])], dim=-1)
    return embedding


class DNN(nn.Module):
    """Authors' models/DNN.py."""

    def __init__(self, in_dims, out_dims, emb_size, time_type="cat", norm=False, dropout=0.5):
        super().__init__()
        self.in_dims, self.out_dims = in_dims, out_dims
        assert out_dims[0] == in_dims[-1], "In and out dimensions must equal to each other."
        self.time_type, self.time_emb_dim, self.norm = time_type, emb_size, norm
        self.emb_layer = nn.Linear(self.time_emb_dim, self.time_emb_dim)
        if self.time_type == "cat":
            in_dims_temp = [self.in_dims[0] + self.time_emb_dim] + self.in_dims[1:]
        else:
            raise ValueError("Unimplemented timestep embedding type %s" % self.time_type)
        out_dims_temp = self.out_dims
        self.in_layers = nn.ModuleList([nn.Linear(d_in, d_out) for d_in, d_out in zip(in_dims_temp[:-1], in_dims_temp[1:])])
        self.out_layers = nn.ModuleList([nn.Linear(d_in, d_out) for d_in, d_out in zip(out_dims_temp[:-1], out_dims_temp[1:])])
        self.drop = nn.Dropout(dropout)
        self.init_weights()

    def init_weights(self):
        for layer in list(self.in_layers) + list(self.out_layers) + [self.emb_layer]:
            size = layer.weight.size()
            std = np.sqrt(2.0 / (size[1] + size[0]))
            layer.weight.data.normal_(0.0, std)
            layer.bias.data.normal_(0.0, 0.001)

    def forward(self, x, timesteps):
        time_emb = timestep_embedding(timesteps, self.time_emb_dim).to(x.device)
        emb = self.emb_layer(time_emb)
        if self.norm:
            x = F.normalize(x)
        x = self.drop(x)
        h = torch.cat([x, emb], dim=-1)
        for layer in self.in_layers:
            h = torch.tanh(layer(h))
        for i, layer in enumerate(self.out_layers):
            h = layer(h)
            if i != len(self.out_layers) - 1:
                h = torch.tanh(h)
        return h


def betas_from_linear_variance(steps, variance, max_beta=0.999):
    alpha_bar = 1 - variance
    betas = [1 - alpha_bar[0]]
    for i in range(1, steps):
        betas.append(min(1 - alpha_bar[i] / alpha_bar[i - 1], max_beta))
    return np.array(betas)


def betas_for_alpha_bar(num_diffusion_timesteps, alpha_bar, max_beta=0.999):
    betas = []
    for i in range(num_diffusion_timesteps):
        t1, t2 = i / num_diffusion_timesteps, (i + 1) / num_diffusion_timesteps
        betas.append(min(1 - alpha_bar(t2) / alpha_bar(t1), max_beta))
    return np.array(betas)


def mean_flat(tensor):
    return tensor.mean(dim=list(range(1, len(tensor.shape))))


class GaussianDiffusion:
    """Authors' models/gaussian_diffusion.py. Not an nn.Module (it holds no parameters; theirs only calls .to(device))."""

    def __init__(self, mean_type, noise_schedule, noise_scale, noise_min, noise_max, steps, device,
                 history_num_per_term=10, beta_fixed=True):
        self.mean_type, self.noise_schedule, self.noise_scale = mean_type, noise_schedule, noise_scale
        self.noise_min, self.noise_max, self.steps, self.device = noise_min, noise_max, steps, device
        self.history_num_per_term = history_num_per_term
        self.Lt_history = np.zeros((steps, history_num_per_term), dtype=np.float64)  # CPU, float64 as theirs
        self.Lt_count = np.zeros(steps, dtype=np.int64)
        if noise_scale != 0.:
            self.betas = th.tensor(self.get_betas(), dtype=th.float64).to(self.device)
            if beta_fixed:
                self.betas[0] = 0.00001
            assert len(self.betas.shape) == 1 and len(self.betas) == self.steps
            assert (self.betas > 0).all() and (self.betas <= 1).all(), "betas out of range"
            self.calculate_for_diffusion()

    def get_betas(self):
        if self.noise_schedule in ("linear", "linear-var"):
            start, end = self.noise_scale * self.noise_min, self.noise_scale * self.noise_max
            if self.noise_schedule == "linear":
                return np.linspace(start, end, self.steps, dtype=np.float64)
            return betas_from_linear_variance(self.steps, np.linspace(start, end, self.steps, dtype=np.float64))
        if self.noise_schedule == "cosine":
            return betas_for_alpha_bar(self.steps, lambda t: math.cos((t + 0.008) / 1.008 * math.pi / 2) ** 2)
        if self.noise_schedule == "binomial":
            return [1 / (self.steps - t + 1) for t in np.arange(self.steps)]
        raise NotImplementedError(f"unknown beta schedule: {self.noise_schedule}!")

    def calculate_for_diffusion(self):
        alphas = 1.0 - self.betas
        self.alphas_cumprod = th.cumprod(alphas, axis=0).to(self.device)
        self.alphas_cumprod_prev = th.cat([th.tensor([1.0]).to(self.device), self.alphas_cumprod[:-1]]).to(self.device)
        self.alphas_cumprod_next = th.cat([self.alphas_cumprod[1:], th.tensor([0.0]).to(self.device)]).to(self.device)
        self.sqrt_alphas_cumprod = th.sqrt(self.alphas_cumprod)
        self.sqrt_one_minus_alphas_cumprod = th.sqrt(1.0 - self.alphas_cumprod)
        self.log_one_minus_alphas_cumprod = th.log(1.0 - self.alphas_cumprod)
        self.sqrt_recip_alphas_cumprod = th.sqrt(1.0 / self.alphas_cumprod)
        self.sqrt_recipm1_alphas_cumprod = th.sqrt(1.0 / self.alphas_cumprod - 1)
        self.posterior_variance = self.betas * (1.0 - self.alphas_cumprod_prev) / (1.0 - self.alphas_cumprod)
        self.posterior_log_variance_clipped = th.log(th.cat([self.posterior_variance[1].unsqueeze(0), self.posterior_variance[1:]]))
        self.posterior_mean_coef1 = self.betas * th.sqrt(self.alphas_cumprod_prev) / (1.0 - self.alphas_cumprod)
        self.posterior_mean_coef2 = (1.0 - self.alphas_cumprod_prev) * th.sqrt(alphas) / (1.0 - self.alphas_cumprod)

    def p_sample(self, model, x_start, steps, sampling_noise=False):
        assert steps <= self.steps, "Too much steps in inference."
        if steps == 0:
            x_t = x_start
        else:
            t = th.tensor([steps - 1] * x_start.shape[0]).to(x_start.device)
            x_t = self.q_sample(x_start, t)
        indices = list(range(self.steps))[::-1]
        if self.noise_scale == 0.:
            for i in indices:
                t = th.tensor([i] * x_t.shape[0]).to(x_start.device)
                x_t = model(x_t, t)
            return x_t
        for i in indices:
            t = th.tensor([i] * x_t.shape[0]).to(x_start.device)
            out = self.p_mean_variance(model, x_t, t)
            if sampling_noise:
                noise = th.randn_like(x_t)
                nonzero_mask = (t != 0).float().view(-1, *([1] * (len(x_t.shape) - 1)))
                x_t = out["mean"] + nonzero_mask * th.exp(0.5 * out["log_variance"]) * noise
            else:
                x_t = out["mean"]
        return x_t

    def training_losses(self, model, x_start, reweight=False):
        batch_size, device = x_start.size(0), x_start.device
        ts, pt = self.sample_timesteps(batch_size, device, "importance")
        noise = th.randn_like(x_start)
        x_t = self.q_sample(x_start, ts, noise) if self.noise_scale != 0. else x_start
        terms = {}
        model_output = model(x_t, ts)
        target = {ModelMeanType.START_X: x_start, ModelMeanType.EPSILON: noise}[self.mean_type]
        assert model_output.shape == target.shape == x_start.shape
        mse = mean_flat((target - model_output) ** 2)
        if reweight:
            if self.mean_type == ModelMeanType.START_X:
                weight = self.SNR(ts - 1) - self.SNR(ts)
                weight = th.where((ts == 0), 1.0, weight)
                loss = mse
            elif self.mean_type == ModelMeanType.EPSILON:
                weight = (1 - self.alphas_cumprod[ts]) / ((1 - self.alphas_cumprod_prev[ts]) ** 2 * (1 - self.betas[ts]))
                weight = th.where((ts == 0), 1.0, weight)
                likelihood = mean_flat((x_start - self._predict_xstart_from_eps(x_t, ts, model_output)) ** 2 / 2.0)
                loss = th.where((ts == 0), likelihood, mse)
        else:
            weight = th.tensor([1.0] * len(target)).to(device)
        terms["loss"] = weight * loss
        # loss history of the importance sampler, one sample after the other as in the authors' loop
        vals = terms["loss"].detach().double().cpu().numpy()
        for t, v in zip(ts.cpu().numpy(), vals):
            if self.Lt_count[t] == self.history_num_per_term:
                self.Lt_history[t, :-1] = self.Lt_history[t, 1:].copy()
                self.Lt_history[t, -1] = v
            else:
                self.Lt_history[t, self.Lt_count[t]] = v
                self.Lt_count[t] += 1
        terms["loss"] /= pt
        return terms

    def sample_timesteps(self, batch_size, device, method="uniform", uniform_prob=0.001):
        if method == "importance":
            if not (self.Lt_count == self.history_num_per_term).all():
                return self.sample_timesteps(batch_size, device, method="uniform")
            Lt_sqrt = th.sqrt(th.mean(th.from_numpy(self.Lt_history) ** 2, axis=-1))
            pt_all = Lt_sqrt / th.sum(Lt_sqrt)
            pt_all *= 1 - uniform_prob
            pt_all += uniform_prob / len(pt_all)
            assert pt_all.sum(-1) - 1. < 1e-5
            t = th.multinomial(pt_all, num_samples=batch_size, replacement=True)
            pt = pt_all.gather(dim=0, index=t) * len(pt_all)
            return t.to(device), pt.to(device)
        if method == "uniform":
            t = th.randint(0, self.steps, (batch_size,), device=device).long()
            return t, th.ones_like(t).float()
        raise ValueError

    def q_sample(self, x_start, t, noise=None):
        if noise is None:
            noise = th.randn_like(x_start)
        assert noise.shape == x_start.shape
        return (self._extract_into_tensor(self.sqrt_alphas_cumprod, t, x_start.shape) * x_start
                + self._extract_into_tensor(self.sqrt_one_minus_alphas_cumprod, t, x_start.shape) * noise)

    def q_posterior_mean_variance(self, x_start, x_t, t):
        assert x_start.shape == x_t.shape
        posterior_mean = (self._extract_into_tensor(self.posterior_mean_coef1, t, x_t.shape) * x_start
                          + self._extract_into_tensor(self.posterior_mean_coef2, t, x_t.shape) * x_t)
        posterior_variance = self._extract_into_tensor(self.posterior_variance, t, x_t.shape)
        posterior_log_variance_clipped = self._extract_into_tensor(self.posterior_log_variance_clipped, t, x_t.shape)
        return posterior_mean, posterior_variance, posterior_log_variance_clipped

    def p_mean_variance(self, model, x, t):
        B, C = x.shape[:2]
        assert t.shape == (B,)
        model_output = model(x, t)
        model_variance = self._extract_into_tensor(self.posterior_variance, t, x.shape)
        model_log_variance = self._extract_into_tensor(self.posterior_log_variance_clipped, t, x.shape)
        if self.mean_type == ModelMeanType.START_X:
            pred_xstart = model_output
        elif self.mean_type == ModelMeanType.EPSILON:
            pred_xstart = self._predict_xstart_from_eps(x, t, eps=model_output)
        else:
            raise NotImplementedError(self.mean_type)
        model_mean, _, _ = self.q_posterior_mean_variance(x_start=pred_xstart, x_t=x, t=t)
        return {"mean": model_mean, "variance": model_variance, "log_variance": model_log_variance, "pred_xstart": pred_xstart}

    def _predict_xstart_from_eps(self, x_t, t, eps):
        assert x_t.shape == eps.shape
        return (self._extract_into_tensor(self.sqrt_recip_alphas_cumprod, t, x_t.shape) * x_t
                - self._extract_into_tensor(self.sqrt_recipm1_alphas_cumprod, t, x_t.shape) * eps)

    def SNR(self, t):
        self.alphas_cumprod = self.alphas_cumprod.to(t.device)
        return self.alphas_cumprod[t] / (1 - self.alphas_cumprod[t])

    def _extract_into_tensor(self, arr, timesteps, broadcast_shape):
        arr = arr.to(timesteps.device)
        res = arr[timesteps].float()
        while len(res.shape) < len(broadcast_shape):
            res = res[..., None]
        return res.expand(broadcast_shape)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diff_lr", type=float, default=1e-4, help="AdamW learning rate (paper/authors: 1e-5 to 1e-3)")
    ap.add_argument("--noise_scale", type=float, default=1e-3, help="authors: 1e-4 to 0.5 per dataset")
    ap.add_argument("--steps", type=int, default=5, help="diffusion steps (authors: 5, 10, 40 per dataset)")
    ap.add_argument("--noise_min", type=float, default=1e-3)
    ap.add_argument("--noise_max", type=float, default=1e-2)
    ap.add_argument("--noise_schedule", default="linear-var")
    ap.add_argument("--mean_type", choices=["x0", "eps"], default="x0")
    ap.add_argument("--sampling_steps", type=int, default=0)
    ap.add_argument("--dims", default="[1000]")
    ap.add_argument("--emb_size", type=int, default=10)
    ap.add_argument("--weight_decay", type=float, default=0.0)
    ap.add_argument("--reweight", type=int, default=1)
    ap.add_argument("--batch_size", type=int, default=400)
    ap.add_argument("--lr", type=float, default=0.0, help="accepted for the pipeline; NOT used (see module doc)")
    ap.add_argument("--reg", type=float, default=0.0, help="accepted for the pipeline; NOT used")
    ap.add_argument("--model", default="lightgcn", help="accepted for the pipeline; NOT used")
    ap.add_argument("--data", required=True)
    ap.add_argument("--train_file", default="train.tsv")
    ap.add_argument("--epochs", type=int, default=1000)
    ap.add_argument("--patience", type=int, default=4, help="evaluations without improvement (authors: 20 epochs = 4 evaluations)")
    ap.add_argument("--eval_every", type=int, default=5)
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
    mean_type = ModelMeanType.START_X if a.mean_type == "x0" else ModelMeanType.EPSILON
    diffusion = GaussianDiffusion(mean_type, a.noise_schedule, a.noise_scale, a.noise_min, a.noise_max, a.steps, dev)
    out_dims = eval(a.dims) + [ni]
    in_dims = out_dims[::-1]
    model = DNN(in_dims, out_dims, a.emb_size, time_type="cat", norm=False).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=a.diff_lr, weight_decay=a.weight_decay)

    def rows_of(users):
        return torch.tensor(train_csr[users.cpu().numpy()].toarray(), device=dev, dtype=torch.float32)

    @torch.no_grad()
    def score_fn(users):
        return diffusion.p_sample(model, rows_of(users), a.sampling_steps, False)

    if dev.type == "cuda":
        torch.cuda.reset_peak_memory_stats(dev)
    t0 = time.time()
    best, best_epoch, bad = -1.0, 0, 0
    hf = open(os.path.join(a.run_dir, "history.jsonl"), "w")
    for epoch in range(1, a.epochs + 1):
        model.train()
        perm = rng.permutation(nu)
        tot = 0.0
        for s in range(0, nu, a.batch_size):
            batch = rows_of(torch.tensor(perm[s:s + a.batch_size]))
            opt.zero_grad()
            loss = diffusion.training_losses(model, batch, bool(a.reweight))["loss"].mean()
            loss.backward()
            opt.step()
            tot += loss.item() * len(batch)
        if epoch % a.eval_every:
            continue
        model.eval()
        v = valid_ndcg_scores(score_fn, nu, train_csr, truths, dev)
        rec = {"epoch": epoch, "loss": tot / nu, "seconds": round(time.time() - t0, 1),
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
        export_topk(score_fn, a.data, a.run_dir, a.train_file, device=dev)
    info = {**vars(a), "loss": "diffusion-mse", "best_valid_ndcg@20": best, "best_epoch": best_epoch, "epochs_run": epoch,
            "train_seconds": round(train_seconds, 1), "export_seconds": round(time.time() - t1, 1),
            "peak_gpu_mb": round(torch.cuda.max_memory_allocated(dev) / 2 ** 20) if dev.type == "cuda" else None}
    json.dump(info, open(os.path.join(a.run_dir, "run.json"), "w"), indent=2)
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
