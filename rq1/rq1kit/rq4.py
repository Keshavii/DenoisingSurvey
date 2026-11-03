"""RQ4: is it the detection signal or the treatment that does the work? One LightGCN-BCE trainer in which a signal
module scores every positive training interaction (higher = more suspicious) and a treatment module acts on the
scores. Signals are leaves of the survey's detection taxonomy (paper Section 4); treatments are its per-sample
treatments (Section 5). Spec: "Denoising Survey: Plan of Action", section "RQ4 specification".

Signals (--signal)
  L1  loss, interaction-wise, no foundation        BCE loss of the positive in the current batch          (T-CE)
  L2  loss, user level, no foundation              loss minus the mean loss of the user's positives        (PLD)
  L3  gradient disagreement, no foundation         1 - cos(sample gradient, mean gradient of all positives) (BOD)
  L4  gradient disagreement, distributional        same, anchor = mean gradient of the memorised set        (SGDL)
  P1  probability, temporal instability            variance of sigmoid(score) over the last 5 epochs       (DeCA, LLMHD)
  P2  probability, cross-model, model-based        |sigmoid(f) - sigmoid(g)|, g = jointly trained MF       (DeCA, CSRec)
  R1  representation similarity, no foundation     1 - cos(item, user's other items) in current embeddings (control)
  R2  representation similarity, metric space      same in a frozen reference LightGCN space               (DA-MRS, DeMBR)
  R3  structure, relational structure              1 - RGCF edge reliability from neighbourhood features   (RGCF, CLID)
  R4  LLM evaluation, metric space                 1 - cos in the LLM item-profile embedding space         (LLMHD)
  R5  LLM evaluation, knowledge-based              Llama P(does not fit), top 20% by loss only             (LLaRD, LLMHD)
  M1  loss, model-based foundation (teacher)       loss under a frozen LightGCN-BCE trained on the same file  (anchored L1)
  M1c loss, model-based, oracle-quality anchor     loss under a frozen LightGCN-BCE trained on the clean base (anchor quality)
  M2  loss, model-based (historical checkpoint)    loss under the model's own snapshot after epoch 5          (anchored L1)
  L5  loss, user level, distributional             loss minus the mean loss of the user's memorised positives (anchored L2)
  none                                             no signal: plain LightGCN-BCE, or random-view reshape

Treatments (--treat) act on positives only; q = the positive's suspicion rank in its batch, 0 (least) to 1 (most).
  drop      T-CE: rank [pos; neg] by suspicion (negatives below every positive), keep the lowest (1 - rate) share,
            rate rising linearly to --rate over --num_gradual iterations; loss = 2 x mean BCE over the kept
  reweight  R-CE style: weight (1 - q) ** --beta on positives, 1 on negatives; loss = 2 x mean weighted BCE
  relabel   DCF style: the top rate share of positives (by q) get target 0 for this step, same schedule as drop
  resample  PLD style: each sampled user picks 1 of --k candidate positives with softmax(-q_cand / --temp),
            from epoch --begin_resample (PLD: 5); q_cand = rank within the user's candidates
  graph_drop      RGCF / DA-MRS / DeMBR style: the top rate share of edges (whole-epoch ranking) is removed from the
                  LightGCN propagation graph for that epoch, same schedule as drop; the loss is untouched
  graph_reweight  RGCF / LLaRD graph-gate style: edge weight (1 - q) ** --beta in the propagation graph, symmetric
                  normalisation by weighted degree; the loss is untouched
  user_reweight   UDT style: every positive of a user gets (1 - q_user) ** --beta, q_user = rank of the user's mean
                  suspicion among users (whole epoch)
  soft_relabel    CSRec / GUIDER style: positive target 1 - --lam x q instead of a hard flip
  reshape         SGL-ED style contrastive reshaping (rq1kit.sgl): two edge-dropout views per epoch, InfoNCE on the
                  batch's users and items (negatives: all users / items of the other view), weight --ssl_reg; loss =
                  mean BCE + ssl_reg x InfoNCE / batch (SGL's sum ratio). With --signal none the views drop edges at
                  random (SGL); with a signal each edge is dropped with probability min(1, 2 ratio q) (mean = ratio)
Interactions without a score (R5 outside the LLM subset, R1/R2/R4 for single-item users, signals before their
history exists) are never treated. L1 with drop reproduces rq1kit.adt T-CE exactly (tests/test_rq4.py).

Every 5 epochs the run logs, for its signal: ROC-AUC against the known noisy positives (noisy > 0 in train.tsv);
hard_auc, the same among the 20% hardest positives (highest loss under the plain reference model of this file); and
stability, the Spearman correlation with the previous logged scores. The scores at the selected epoch are saved as
signal_scores.npy (float16, edges in (user, item) order), for seed stability and RQ3.

  python -m rq1kit.rq4 --signal L1 --treat drop --rate 0.1 --data data/ml1m --train_file train_N3_20_s1.tsv \
      --lr 1e-3 --reg 1e-5 --seed 1 --run_dir runs/rq4/ml1m/L1_drop_N3_20_s1
"""
import argparse
import fcntl
import hashlib
import json
import os
import pickle
import shutil
import subprocess
import sys
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .adt import drop_rate_schedule
from .backbone import Backbone, norm_adj, sample_negatives, valid_ndcg
from .data import load_split, to_csr
from .export import export_topk
from .pld import sample_candidates
from .sgl import propagate_with

SIGNALS = ["none", "L1", "L2", "L3", "L4", "P1", "P2", "R1", "R2", "R3", "R4", "R5", "M1", "M1c", "M2", "L5"]
TREATS = ["none", "drop", "reweight", "relabel", "resample", "graph_drop", "graph_reweight", "user_reweight", "soft_relabel",
          "reshape"]
EPOCH_TREATS = ("graph_drop", "graph_reweight", "user_reweight")  # act on whole-epoch scores
HISTORY = 5          # epochs of history for P1 and for the memorised set of L4 (SGDL's memorisation phase)


# ----------------------------------------------------------------------------------------------- helpers
def batch_rank(s):
    """Rank of each finite value among the finite values of s, scaled to [0, 1]; NaN stays NaN."""
    q = torch.full_like(s, float("nan"))
    ok = torch.isfinite(s)
    n = int(ok.sum())
    if n == 1:
        q[ok] = 0.5
    elif n > 1:
        order = torch.argsort(s[ok], stable=True)
        r = torch.empty(n, device=s.device)
        r[order] = torch.arange(n, device=s.device, dtype=r.dtype)
        q[ok] = r / (n - 1)
    return q


def row_rank(s):
    """Rank within each row scaled to [0, 1] (resample: rank of a candidate among the user's candidates).
    Unscored candidates (NaN) get 0.5; a row with one column gets 0."""
    k = s.shape[1]
    if k == 1:
        return torch.zeros_like(s)
    nan = ~torch.isfinite(s)
    filled = torch.where(nan, torch.full_like(s, float("inf")), s)
    r = torch.argsort(torch.argsort(filled, dim=1, stable=True), dim=1).float() / (k - 1)
    return torch.where(nan, torch.full_like(r, 0.5), r)


def spearman(a, b):
    """Spearman rank correlation over entries finite in both; None if fewer than 3."""
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 3:
        return None
    ra, rb = np.argsort(np.argsort(a[ok], kind="mergesort")), np.argsort(np.argsort(b[ok], kind="mergesort"))
    c = np.corrcoef(ra, rb)[0, 1]
    return None if not np.isfinite(c) else float(c)


def roc_auc(score, label):
    """ROC-AUC of score against binary label (ties counted half); NaN scores are dropped. None if one class only."""
    ok = np.isfinite(score)
    s, y = score[ok], label[ok].astype(bool)
    npos, nneg = int(y.sum()), int((~y).sum())
    if npos == 0 or nneg == 0:
        return None
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s))
    ss = s[order]
    i = 0
    while i < len(ss):  # average ranks over ties
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return float((ranks[y].sum() - npos * (npos + 1) / 2) / (npos * nneg))


def centroid_dissimilarity(E_items, eu, ei, nu):
    """1 - cos(item vector, mean vector of the user's other positives); NaN for users with one positive."""
    E = F.normalize(E_items, dim=1)
    s = torch.zeros(nu, E.shape[1], device=E.device).index_add_(0, eu, E[ei])
    cnt = torch.bincount(eu, minlength=nu).float()
    other = s[eu] - E[ei]
    c = cnt[eu] - 1
    cos = F.cosine_similarity(E[ei], other / c.clamp(min=1)[:, None], dim=1)
    return torch.where(c > 0, 1 - cos, torch.full_like(cos, float("nan")))


# ----------------------------------------------------------------------------------------------- signals
class SignalState:
    """Holds what a signal needs between steps; `epoch_cache` refreshes it once per epoch from the current model,
    `batch` returns the suspicion of the given positive edges."""

    def __init__(self, name, eu, ei, nu, ni, dev, ref_items=None, llm_items=None, llm_scores=None, aux=None, teacher=None):
        self.name, self.eu, self.ei, self.nu, self.ni, self.dev = name, eu, ei, nu, ni, dev
        self.cache = None
        self.prob_hist = []          # P1 and L4: sigmoid(score) of every edge for the last HISTORY epochs
        self.memorised = None        # L4: edges fitted (prob > 0.5) in every one of the first HISTORY epochs
        self.static = None
        self.aux = aux               # P2: (MF model, optimiser)
        if name == "R2":
            self.static = centroid_dissimilarity(ref_items, eu, ei, nu)
        elif name == "R4":
            self.static = centroid_dissimilarity(llm_items, eu, ei, nu)
        elif name == "R5":
            self.static = llm_scores
        elif name in ("M1", "M1c"):
            self.static = teacher

    @torch.no_grad()
    def epoch_cache(self, model, epoch):
        if self.name in ("none", "L1", "P2", "R2", "R4", "R5", "M1", "M1c"):
            return
        if self.name == "M2" and self.cache is not None and torch.isfinite(self.cache).any():
            return  # the snapshot is frozen once taken
        U, I = model.propagate()
        x = (U[self.eu] * I[self.ei]).sum(1)
        p = torch.sigmoid(x)
        if self.name == "M2":  # SGDL's memorisation point: the model after HISTORY epochs, frozen as the anchor
            self.cache = F.softplus(-x) if epoch > HISTORY else torch.full_like(x, float("nan"))
            return
        if self.name == "L5":
            self.prob_hist = (self.prob_hist + [p])[-HISTORY:]
            if self.memorised is None and len(self.prob_hist) == HISTORY:
                m = torch.stack(self.prob_hist).gt(0.5).all(0)
                self.memorised = m if m.any() else p.ge(p.median())
            if self.memorised is None:
                self.cache = torch.full_like(x, float("nan"))
                return
            loss = F.softplus(-x)
            m = self.memorised.float()
            cnt = torch.zeros(self.nu, device=self.dev).index_add_(0, self.eu, m)
            mem_mean = torch.zeros(self.nu, device=self.dev).index_add_(0, self.eu, loss * m) / cnt.clamp(min=1)
            all_mean = torch.zeros(self.nu, device=self.dev).index_add_(0, self.eu, loss) / \
                torch.bincount(self.eu, minlength=self.nu).float().clamp(min=1)
            anchor = torch.where(cnt > 0, mem_mean, all_mean)  # users with nothing memorised: their own mean
            self.cache = loss - anchor[self.eu]
            return
        if self.name == "L2":
            loss = F.softplus(-x)
            mean_u = torch.zeros(self.nu, device=self.dev).index_add_(0, self.eu, loss) / \
                torch.bincount(self.eu, minlength=self.nu).float().clamp(min=1)
            self.cache = loss - mean_u[self.eu]
        elif self.name in ("L3", "L4"):
            self.prob_hist = (self.prob_hist + [p])[-HISTORY:]
            if self.name == "L4" and self.memorised is None and len(self.prob_hist) == HISTORY:
                m = torch.stack(self.prob_hist).gt(0.5).all(0)
                self.memorised = m if m.any() else p.ge(p.median())
            if self.name == "L4":
                anchor = self.memorised
                if anchor is None:
                    self.cache = torch.full_like(x, float("nan"))
                    return
            else:
                anchor = torch.ones_like(p, dtype=torch.bool)
            # BCE on a positive: d loss / d(U_u, I_i) = -(1 - p) (I_i, U_u). Anchor gradient, summed over anchor edges
            # and scattered to the user and item rows; the per-edge cosine against it is taken in that row space.
            c = -(1 - p)
            GU = torch.zeros_like(U).index_add_(0, self.eu[anchor], (c[anchor, None] * I[self.ei[anchor]]))
            GI = torch.zeros_like(I).index_add_(0, self.ei[anchor], (c[anchor, None] * U[self.eu[anchor]]))
            norm = torch.sqrt(GU.pow(2).sum() + GI.pow(2).sum()).clamp(min=1e-12)
            dot = c * ((I[self.ei] * GU[self.eu]).sum(1) + (U[self.eu] * GI[self.ei]).sum(1))
            gnorm = (c.abs() * torch.sqrt(I[self.ei].pow(2).sum(1) + U[self.eu].pow(2).sum(1))).clamp(min=1e-12)
            self.cache = 1 - dot / (gnorm * norm)
        elif self.name == "P1":
            self.prob_hist = (self.prob_hist + [p])[-HISTORY:]
            self.cache = torch.stack(self.prob_hist).var(0, unbiased=False) if len(self.prob_hist) >= 2 \
                else torch.full_like(p, float("nan"))
        elif self.name == "R1":
            self.cache = centroid_dissimilarity(I, self.eu, self.ei, self.nu)
        elif self.name == "R3":
            ego_u, ego_i = model.user.weight, model.item.weight
            uf = torch.zeros_like(ego_u).index_add_(0, self.eu, ego_i[self.ei])     # RGCF: user = sum of its items
            itf = torch.zeros_like(ego_i).index_add_(0, self.ei, ego_u[self.eu])    # item = sum of its users
            cos = F.cosine_similarity(uf[self.eu], itf[self.ei], dim=1)
            self.cache = 1 - (cos + 1) / 2

    def batch(self, edges, pos_logit=None, u=None, p=None):
        if self.name == "none":
            return None
        if self.name == "L1":
            return F.softplus(-pos_logit.detach())
        if self.name == "P2":
            g = self.aux[0]
            with torch.no_grad():
                gp = (g.user(u) * g.item(p)).sum(1)
            return (torch.sigmoid(pos_logit.detach()) - torch.sigmoid(gp)).abs()
        src = self.static if self.static is not None else self.cache
        return src[edges]

    @torch.no_grad()
    def all_scores(self, model):
        """Suspicion of every positive edge right now (for the detection AUC)."""
        if self.name in ("none",):
            return None
        if self.name in ("L1", "P2"):
            U, I = model.propagate()
            x = (U[self.eu] * I[self.ei]).sum(1)
            if self.name == "L1":
                return F.softplus(-x)
            g = self.aux[0]
            gx = (g.user.weight[self.eu] * g.item.weight[self.ei]).sum(1)
            return (torch.sigmoid(x) - torch.sigmoid(gx)).abs()
        return self.static if self.static is not None else self.cache


# ----------------------------------------------------------------------------------------------- treatments
def weighted_adj(eu, ei, w, nu, ni):
    """LightGCN's symmetric normalised adjacency with edge weights w (0 removes an edge)."""
    r = torch.cat([eu, ei + nu])
    c = torch.cat([ei + nu, eu])
    ww = torch.cat([w, w])
    deg = torch.zeros(nu + ni, device=w.device).index_add_(0, r, ww)
    dinv = torch.where(deg > 0, deg.pow(-0.5), torch.zeros_like(deg))
    keep = ww > 0
    return torch.sparse_coo_tensor(torch.stack([r[keep], c[keep]]), (dinv[r] * ww * dinv[c])[keep],
                                   (nu + ni, nu + ni)).coalesce()


def epoch_weights(treat, scores, eu, nu, rate, beta):
    """Per-edge weights for the whole-epoch treatments from every edge's suspicion (NaN = unscored = weight 1)."""
    q = batch_rank(scores)
    if treat == "graph_drop":
        n = int(rate * int(torch.isfinite(q).sum()))
        w = torch.ones_like(scores)
        if n > 0:
            qq = torch.where(torch.isfinite(q), q, torch.full_like(q, -1.0))
            w[torch.argsort(qq, descending=True, stable=True)[:n]] = 0.0
        return w
    if treat == "graph_reweight":
        return torch.where(torch.isfinite(q), (1 - q).clamp(min=0) ** beta, torch.ones_like(q))
    if treat == "user_reweight":
        ok = torch.isfinite(scores)
        tot = torch.zeros(nu, device=scores.device).index_add_(0, eu[ok], scores[ok])
        cnt = torch.zeros(nu, device=scores.device).index_add_(0, eu[ok], torch.ones_like(scores[ok]))
        m = torch.where(cnt > 0, tot / cnt.clamp(min=1), torch.full_like(tot, float("nan")))
        qu = batch_rank(m)
        wu = torch.where(torch.isfinite(qu), (1 - qu).clamp(min=0) ** beta, torch.ones_like(qu))
        return wu[eu]
    raise ValueError(treat)


def treated_loss(treat, pos, neg, susp, rate, beta, lam=0.5, w_epoch=None):
    """Loss of one batch of (positive, negative) logits under a treatment; susp = suspicion of the positives,
    w_epoch = the positives' whole-epoch weights (user_reweight)."""
    if treat == "user_reweight" and w_epoch is not None:
        return 2 * torch.cat([F.softplus(-pos) * w_epoch, F.softplus(neg)]).mean()
    if treat in ("none", "resample", "graph_drop", "graph_reweight", "user_reweight", "reshape") or susp is None:
        return -(F.logsigmoid(pos) + F.logsigmoid(-neg)).mean()
    q = batch_rank(susp)
    if treat == "drop":
        # rq1kit.adt.tce_loss with the ranking key [q + 1 (scored positives); 0.5 (unscored); 0 (negatives)]: the
        # same kept set as ranking by loss * label when the signal is the loss itself.
        y = torch.cat([pos, neg])
        t = torch.cat([torch.ones_like(pos), torch.zeros_like(neg)])
        key = torch.cat([torch.where(torch.isfinite(q), q + 1, torch.full_like(q, 0.5)), torch.zeros_like(neg)])
        if susp is not None and torch.isfinite(susp).all() and (susp > 0).all():
            key = torch.cat([susp, torch.zeros_like(neg)])  # identical order; keeps T-CE's own key for L1
        keep = torch.argsort(key)[: int((1 - rate) * len(key))]
        return 2 * F.binary_cross_entropy_with_logits(y[keep], t[keep])
    if treat == "reweight":
        w = torch.where(torch.isfinite(q), (1 - q).clamp(min=0) ** beta, torch.ones_like(q))
        loss = torch.cat([F.softplus(-pos) * w, F.softplus(neg)])
        return 2 * loss.mean()
    if treat == "relabel":
        n_flip = int(rate * len(pos))
        target = torch.ones_like(pos)
        if n_flip > 0:
            qq = torch.where(torch.isfinite(q), q, torch.full_like(q, -1.0))
            target[torch.argsort(qq, descending=True, stable=True)[:n_flip]] = 0.0
        return F.binary_cross_entropy_with_logits(pos, target) + F.softplus(neg).mean()
    if treat == "soft_relabel":
        target = torch.where(torch.isfinite(q), 1 - lam * q, torch.ones_like(q))
        return F.binary_cross_entropy_with_logits(pos, target) + F.softplus(neg).mean()
    raise ValueError(treat)


# ----------------------------------------------------------------------------------------------- inputs
def reference_model(a, dev):
    """Plain LightGCN-BCE on this training file (tuned Plain-BCE settings), trained once and cached; returns its
    propagated user and item embeddings (numpy). Used by R2 (frozen metric space) and by rq4_llm (the 20% cap)."""
    key = hashlib.md5(json.dumps([a.data, a.train_file, a.dim, a.layers, a.lr, a.reg, a.ref_epochs]).encode()).hexdigest()[:10]
    cache = os.path.join(a.ref_root, f"{os.path.basename(os.path.normpath(a.data))}_{os.path.splitext(a.train_file)[0]}_{key}")
    os.makedirs(a.ref_root, exist_ok=True)
    lockf = open(cache + ".lock", "w")
    fcntl.flock(lockf, fcntl.LOCK_EX)  # one job trains it, the others wait and reuse it
    if not os.path.isfile(os.path.join(cache, "emb.npz")):
        tmp = f"{cache}.tmp{os.getpid()}"
        shutil.rmtree(tmp, ignore_errors=True)
        cmd = [sys.executable, "-m", "rq1kit.backbone", "--data", a.data, "--train_file", a.train_file, "--model", "lightgcn",
               "--loss", "bce", "--dim", str(a.dim), "--layers", str(a.layers), "--lr", str(a.lr), "--reg", str(a.reg),
               "--epochs", str(a.ref_epochs), "--patience", "20", "--seed", "0", "--no_export", "--device", a.device,
               "--run_dir", tmp]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
        meta = json.load(open(os.path.join(a.data, "meta.json")))
        _, train, *_ = load_split(a.data, a.train_file)
        csr = to_csr(train, meta["n_users"], meta["n_items"])
        with torch.random.fork_rng(devices=[]):  # building the module must not move the caller's random stream
            m = Backbone(meta["n_users"], meta["n_items"], a.dim, "lightgcn", a.layers, norm_adj(csr, torch.device("cpu")))
        m.load_state_dict(torch.load(os.path.join(tmp, "best.pt"), map_location="cpu", weights_only=True))
        with torch.no_grad():
            U, I = m.propagate()
        np.savez(os.path.join(tmp, "emb.npz"), U=U.numpy(), I=I.numpy())
        shutil.rmtree(cache, ignore_errors=True)
        os.rename(tmp, cache)
    fcntl.flock(lockf, fcntl.LOCK_UN)
    lockf.close()
    e = np.load(os.path.join(cache, "emb.npz"))
    return e["U"], e["I"], cache


def build_name(train_file):
    b = os.path.splitext(os.path.basename(train_file))[0]
    return "N0" if b == "train" else b.replace("train_", "")


def llm_item_embeddings(data_dir):
    """bge embeddings of the LLM item profiles (rq1kit.llard_knowledge); identical for every build."""
    d = os.path.join(data_dir, "llard")
    for b in ["N0"] + sorted(os.listdir(d)) if os.path.isdir(d) else []:
        p = os.path.join(d, b, "prf_k", "itm_emb_np.pkl")
        if os.path.isfile(p):
            return np.asarray(pickle.load(open(p, "rb")), dtype=np.float32)
    raise SystemExit(f"R4 needs LLM item-profile embeddings under {d}/<build>/prf_k/itm_emb_np.pkl")


def llm_scores(data_dir, train_file, keys, ni):
    """R5: P(does not fit) from rq1kit.rq4_llm for this training file; NaN for edges outside the scored subset."""
    p = os.path.join(data_dir, "rq4_llm", f"{build_name(train_file)}.npz")
    if not os.path.isfile(p):
        raise SystemExit(f"R5 needs the LLM scores {p} (python -m rq1kit.rq4_llm ...)")
    z = np.load(p)
    out = np.full(len(keys), np.nan, dtype=np.float32)
    k = z["user"].astype(np.int64) * ni + z["item"]
    pos = np.searchsorted(keys, k)
    ok = (pos < len(keys)) & (keys[np.minimum(pos, len(keys) - 1)] == k)
    out[pos[ok]] = z["p_noise"][ok]
    return out


# ----------------------------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--signal", choices=SIGNALS, default="none")
    ap.add_argument("--treat", choices=TREATS, default="none")
    ap.add_argument("--rate", type=float, default=0.1, help="drop / relabel: final share (T-CE epsilon_max)")
    ap.add_argument("--num_gradual", type=int, default=30000, help="drop / relabel: iterations to reach --rate (T-CE)")
    ap.add_argument("--beta", type=float, default=0.5, help="reweight: exponent of (1 - q)")
    ap.add_argument("--temp", type=float, default=0.1, help="resample: softmax temperature (PLD tau)")
    ap.add_argument("--lam", type=float, default=0.5, help="soft_relabel: target 1 - lam x q")
    ap.add_argument("--ssl_reg", type=float, default=0.1, help="reshape: weight of the InfoNCE term (SGL default 0.1)")
    ap.add_argument("--ssl_temp", type=float, default=0.2, help="reshape: InfoNCE temperature (SGL default 0.2)")
    ap.add_argument("--ssl_ratio", type=float, default=0.1, help="reshape: mean edge dropout per view (SGL default 0.1)")
    ap.add_argument("--hard_share", type=float, default=0.2, help="share of hardest positives for hard_auc")
    ap.add_argument("--k", type=int, default=5, help="resample: candidates per user (PLD default 5)")
    ap.add_argument("--begin_resample", type=int, default=5, help="resample: first 0-based epoch (PLD begin_adv 5)")
    ap.add_argument("--aux_dim", type=int, default=32, help="P2: dimension of the auxiliary MF (DeCA 32)")
    ap.add_argument("--aux_lr", type=float, default=1e-3, help="P2: learning rate of the auxiliary MF (DeCA 1e-3)")
    ap.add_argument("--data", required=True)
    ap.add_argument("--train_file", default="train.tsv")
    ap.add_argument("--dim", type=int, default=64)
    ap.add_argument("--layers", type=int, default=3)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--reg", type=float, default=1e-4)
    ap.add_argument("--batch", type=int, default=2048)
    ap.add_argument("--epochs", type=int, default=300)
    ap.add_argument("--patience", type=int, default=20)
    ap.add_argument("--auc_every", type=int, default=5)
    ap.add_argument("--select", choices=["valid_clean", "valid_noisy"], default="valid_clean")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--run_dir", required=True)
    ap.add_argument("--ref_root", default="runs/_rq4_ref")
    ap.add_argument("--ref_epochs", type=int, default=300)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--no_export", action="store_true")
    ap.add_argument("--make_ref", action="store_true", help="only train (or find) the reference model and print its folder")
    a = ap.parse_args(argv)
    if a.make_ref:
        print(reference_model(a, torch.device(a.device))[2])
        return
    assert a.treat in ("none", "reshape") or a.signal != "none", "this treatment needs a signal"
    assert a.treat != "none" or a.signal == "none", "a signal needs a treatment"

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
    noisy_of = dict(zip(train["user"].values.astype(np.int64) * ni + train["item"].values, train["noisy"].values > 0))
    noisy = np.array([noisy_of[k] for k in keys])
    adj = norm_adj(train_csr, dev)
    model = Backbone(nu, ni, a.dim, "lightgcn", a.layers, adj).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=a.lr)
    users_all, items_all = train["user"].values, train["item"].values          # training order as in rq1kit.adt
    edge_of_row = np.searchsorted(keys, users_all.astype(np.int64) * ni + items_all)
    eu = torch.tensor(keys // ni, device=dev)
    ei = torch.tensor(keys % ni, device=dev)
    indptr, indices = train_csr.indptr.astype(np.int64), train_csr.indices.astype(np.int64)

    aux = None
    if a.signal == "P2":
        g = Backbone(nu, ni, a.aux_dim, "mf", 0).to(dev)
        nn.init.normal_(g.user.weight, std=0.01)
        nn.init.normal_(g.item.weight, std=0.01)
        aux = (g, torch.optim.Adam(g.parameters(), lr=a.aux_lr))
    ref_items = llm_items = scores = None
    if a.signal == "R2":
        _, I_ref, _ = reference_model(a, dev)
        ref_items = torch.tensor(I_ref, device=dev)
    if a.signal == "R4":
        llm_items = torch.tensor(llm_item_embeddings(a.data), device=dev)
    if a.signal == "R5":
        scores = torch.tensor(llm_scores(a.data, a.train_file, keys, ni), device=dev)
    teacher = hard = None
    if a.signal in ("M1", "M1c"):
        ta = argparse.Namespace(**{**vars(a), "train_file": "train_clean.tsv" if a.signal == "M1c" else a.train_file})
        U_t, I_t, _ = reference_model(ta, dev)
        U_t, I_t = torch.tensor(U_t, device=dev), torch.tensor(I_t, device=dev)
        teacher = F.softplus(-(U_t[eu] * I_t[ei]).sum(1))
    if a.signal != "none":  # hard positives: the hard_share with the highest loss under this file's reference model
        U_r, I_r, _ = reference_model(a, dev)
        ref_loss = np.logaddexp(0, -(U_r[keys // ni] * I_r[keys % ni]).sum(1))
        hard = np.zeros(len(keys), bool)
        hard[np.argsort(-ref_loss, kind="mergesort")[: int(round(a.hard_share * len(keys)))]] = True
    sig = SignalState(a.signal, eu, ei, nu, ni, dev, ref_items, llm_items, scores, aux, teacher)
    gen = torch.Generator(device=dev).manual_seed(a.seed)  # reshape views

    if dev.type == "cuda":
        torch.cuda.reset_peak_memory_stats(dev)
    t0 = time.time()
    best, best_epoch, bad, it = -1.0, 0, 0, 0
    best_graph_w = best_scores = prev_scores = None
    hf = open(os.path.join(a.run_dir, "history.jsonl"), "w")
    for epoch in range(1, a.epochs + 1):
        model.train()
        sig.epoch_cache(model, epoch)
        w_epoch = None
        if a.treat in EPOCH_TREATS:
            sc = sig.all_scores(model)
            if sc is not None:
                r_now = drop_rate_schedule(it, a.rate, 1.0, a.num_gradual)
                w_epoch = epoch_weights(a.treat, sc.float(), eu, nu, r_now, a.beta)
                if a.treat in ("graph_drop", "graph_reweight"):
                    model.adj = weighted_adj(eu, ei, w_epoch, nu, ni)
        views = None
        if a.treat == "reshape":
            sc = sig.all_scores(model) if a.signal != "none" else None
            views = []
            for _ in range(2):
                if sc is None:   # SGL-ED: keep int(n (1 - ratio)) edges uniformly
                    w = torch.zeros(len(keys), device=dev)
                    w[torch.randperm(len(keys), device=dev, generator=gen)[: int(len(keys) * (1 - a.ssl_ratio))]] = 1.0
                else:            # signal-guided: drop probability min(1, 2 ratio q), same mean as SGL's ratio
                    q = batch_rank(sc.float())
                    pdrop = torch.where(torch.isfinite(q), (2 * a.ssl_ratio * q).clamp(max=1), torch.full_like(q, a.ssl_ratio))
                    w = (torch.rand(len(keys), device=dev, generator=gen) >= pdrop).float()
                views.append(weighted_adj(eu, ei, w, nu, ni))
        perm = rng.permutation(len(users_all))
        neg_all = sample_negatives(users_all[perm], ni, keys, rng)
        resample = a.treat == "resample" and epoch - 1 >= a.begin_resample
        tot = 0.0
        for s in range(0, len(perm), a.batch):
            idx = perm[s:s + a.batch]
            u = torch.tensor(users_all[idx], device=dev)
            n = torch.tensor(neg_all[s:s + a.batch], device=dev)
            U, I = model.propagate()
            if resample:
                cand = sample_candidates(users_all[idx], a.k, indptr, indices, rng)
                cand_t = torch.tensor(cand, device=dev)
                cand_e = torch.tensor(np.searchsorted(keys, users_all[idx][:, None].astype(np.int64) * ni + cand), device=dev)
                with torch.no_grad():
                    cl = (U[u][:, None, :] * I[cand_t]).sum(-1)
                    cs = sig.batch(cand_e.reshape(-1), cl.reshape(-1), u.repeat_interleave(a.k), cand_t.reshape(-1))
                    qr = row_rank(cs.reshape(len(idx), a.k))
                    pick = torch.multinomial(torch.softmax(-qr / a.temp, dim=1), 1).squeeze(1)
                p = cand_t.gather(1, pick[:, None]).squeeze(1)
                edges = cand_e.gather(1, pick[:, None]).squeeze(1)
            else:
                p = torch.tensor(items_all[idx], device=dev)
                edges = torch.tensor(edge_of_row[idx], device=dev)
            su, sp, sn = U[u], I[p], I[n]
            pos, negs = (su * sp).sum(1), (su * sn).sum(1)
            susp = sig.batch(edges, pos, u, p)
            rate = drop_rate_schedule(it, a.rate, 1.0, a.num_gradual) if a.treat in ("drop", "relabel") else 0.0
            loss = treated_loss(a.treat, pos, negs, susp, rate, a.beta, a.lam,
                                w_epoch[edges] if a.treat == "user_reweight" and w_epoch is not None else None)
            reg = (model.user(u).pow(2).sum() + model.item(p).pow(2).sum() + model.item(n).pow(2).sum()) / (2 * len(idx))
            loss = loss + a.reg * reg
            if views is not None:  # rq1kit.sgl's InfoNCE on the two views, scaled per batch like SGL's sums
                (U1, I1), (U2, I2) = (propagate_with(model, g) for g in views)
                U1, I1, U2, I2 = (F.normalize(x, dim=1) for x in (U1, I1, U2, I2))
                u1, u2, i1, i2 = U1[u], U2[u], I1[p], I2[p]
                ssl_u = (u1 @ U2.T) - (u1 * u2).sum(1, keepdim=True)
                ssl_i = (i1 @ I2.T) - (i1 * i2).sum(1, keepdim=True)
                infonce = torch.logsumexp(ssl_u / a.ssl_temp, 1).sum() + torch.logsumexp(ssl_i / a.ssl_temp, 1).sum()
                loss = loss + a.ssl_reg * infonce / len(idx)
            opt.zero_grad()
            loss.backward()
            opt.step()
            if aux is not None:  # DeCA's auxiliary model: plain BCE on the same batch
                g, gopt = aux
                gl = -(F.logsigmoid((g.user(u) * g.item(p)).sum(1)) + F.logsigmoid(-(g.user(u) * g.item(n)).sum(1))).mean()
                gopt.zero_grad()
                gl.backward()
                gopt.step()
            tot += loss.item() * len(idx)
            it += 1
        model.eval()
        v = valid_ndcg(model, train_csr, truths, dev)
        rec = {"epoch": epoch, "iteration": it, "loss": tot / len(perm), "seconds": round(time.time() - t0, 1),
               **{f"{k}_ndcg@20": x for k, x in v.items()}}
        if a.signal != "none" and (epoch == 1 or epoch % a.auc_every == 0):
            sc = sig.all_scores(model)
            if sc is not None:
                scn = sc.float().cpu().numpy()
                rec["detection_auc"] = roc_auc(scn, noisy)
                rec["hard_auc"] = roc_auc(scn[hard], noisy[hard])
                rec["stability"] = spearman(scn, prev_scores) if prev_scores is not None else None
                prev_scores = scn
        hf.write(json.dumps(rec) + "\n"); hf.flush()
        print(rec, flush=True)
        if v[a.select] > best:
            best, best_epoch, bad = v[a.select], epoch, 0
            torch.save(model.state_dict(), os.path.join(a.run_dir, "best.pt"))
            best_graph_w = w_epoch.clone() if a.treat in ("graph_drop", "graph_reweight") and w_epoch is not None else None
            if a.signal != "none":
                sc = sig.all_scores(model)
                best_scores = None if sc is None else sc.float().cpu().numpy()
        else:
            bad += 1
            if bad >= a.patience:
                break
    train_seconds = time.time() - t0
    model.load_state_dict(torch.load(os.path.join(a.run_dir, "best.pt"), map_location=dev, weights_only=True))
    if a.treat in ("graph_drop", "graph_reweight"):  # score with the graph the best epoch was evaluated on
        model.adj = weighted_adj(eu, ei, best_graph_w, nu, ni) if best_graph_w is not None else adj
    model.eval()
    if best_scores is not None:
        np.save(os.path.join(a.run_dir, "signal_scores.npy"), best_scores.astype(np.float16))
    t1 = time.time()
    if not a.no_export:
        with torch.no_grad():
            U, I = model.propagate()
        export_topk(lambda users: U[users] @ I.T, a.data, a.run_dir, a.train_file, device=dev)
    final = {}
    if best_scores is not None:
        final = {"detection_auc_best": roc_auc(best_scores, noisy), "hard_auc_best": roc_auc(best_scores[hard], noisy[hard])}
    info = {**vars(a), "model": "lightgcn", "loss": "bce", "n_noisy_train": int(noisy.sum()), **final,
            "n_noisy_hard": int(noisy[hard].sum()) if hard is not None else None, "best_valid_ndcg@20": best,
            "best_epoch": best_epoch, "epochs_run": epoch, "iterations": it, "train_seconds": round(train_seconds, 1),
            "export_seconds": round(time.time() - t1, 1),
            "peak_gpu_mb": round(torch.cuda.max_memory_allocated(dev) / 2 ** 20) if dev.type == "cuda" else None}
    json.dump(info, open(os.path.join(a.run_dir, "run.json"), "w"), indent=2)
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
