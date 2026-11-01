"""Tests for the SGL adapter (rq1kit/sgl.py). CPU, about a minute.

  cd ~/rq1-kit && python tests/test_sgl.py

1. Edge-dropout sub-graph: keeps int(n * (1 - rho)) distinct training edges, is symmetric, and carries the symmetric
   normalisation of the kept graph (recomputed degrees).
2. The loss equals the authors' lines (_LightGCN.forward and SGL.train_model of SGL-Torch @ c563288, transcribed).
3. With the contrastive weight 0 SGL trains like Plain-BPR (summed loss, as the authors, versus the kit's mean loss:
   the same direction up to Adam's epsilon), and a normal run exports top-K lists with no seen-item leak.
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import torch
import torch.nn.functional as F

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT)
sys.path.insert(0, os.path.join(KIT, "tests"))
from rq1kit.sgl import edge_dropout_adj, sgl_loss  # noqa: E402
from test_partc import make_dataset  # noqa: E402

PY = [sys.executable, "-m"]
ENV = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONPATH": KIT}


def test_subgraph():
    nu, ni, n = 30, 40, 400
    rng = np.random.default_rng(0)
    pairs = np.unique(np.stack([rng.integers(0, nu, n), rng.integers(0, ni, n)], 1), axis=0)
    u, i = torch.tensor(pairs[:, 0]), torch.tensor(pairs[:, 1])
    gen = torch.Generator().manual_seed(1)
    for rho in (0.1, 0.3, 0.5):
        g = edge_dropout_adj(u, i, nu, ni, rho, gen)
        dense = g.to_dense()
        kept = int(len(u) * (1 - rho))
        assert int((dense > 0).sum()) == 2 * kept, (rho, int((dense > 0).sum()), kept)
        assert torch.allclose(dense, dense.T)
        a = (dense > 0).float()
        deg = a.sum(1)
        expect = a / torch.sqrt(deg[:, None].clamp(min=1) * deg[None, :].clamp(min=1))
        assert torch.allclose(dense, expect, atol=1e-6)
        assert (dense[:nu, :nu] == 0).all() and (dense[nu:, nu:] == 0).all()
    print("ok  edge-dropout sub-graph: int(n(1-rho)) edges, symmetric, normalisation of the kept graph (rho 0.1, 0.3, 0.5)")


def test_loss_matches_authors():
    g = torch.Generator().manual_seed(3)
    nu, ni, d, B = 25, 60, 16, 32
    tables = [torch.randn(nu + ni, d, generator=g) for _ in range(3)]
    U, I = tables[0][:nu], tables[0][nu:]
    U1, I1 = tables[1][:nu], tables[1][nu:]
    U2, I2 = tables[2][:nu], tables[2][nu:]
    u = torch.randint(0, nu, (B,), generator=g)
    p = torch.randint(0, ni, (B,), generator=g)
    n = torch.randint(0, ni, (B,), generator=g)
    raw_u, raw_p, raw_n = torch.randn(B, d, generator=g), torch.randn(B, d, generator=g), torch.randn(B, d, generator=g)
    for ssl_reg, tau, reg in ((0.1, 0.2, 1e-4), (0.5, 0.5, 1e-3), (0.005, 1.0, 0.0)):
        mine, _, _ = sgl_loss(U, I, U1, I1, U2, I2, u, p, n, ssl_reg, tau, reg, raw_u, raw_p, raw_n)
        # the authors' lines
        user_embeddings1, item_embeddings1 = F.normalize(U1, dim=1), F.normalize(I1, dim=1)
        user_embeddings2, item_embeddings2 = F.normalize(U2, dim=1), F.normalize(I2, dim=1)
        user_embs, item_embs, neg_item_embs = F.embedding(u, U), F.embedding(p, I), F.embedding(n, I)
        user_embs1, item_embs1 = F.embedding(u, user_embeddings1), F.embedding(p, item_embeddings1)
        user_embs2, item_embs2 = F.embedding(u, user_embeddings2), F.embedding(p, item_embeddings2)
        sup_logits = torch.sum(user_embs * item_embs, -1) - torch.sum(user_embs * neg_item_embs, -1)
        pos_ratings_user = torch.sum(user_embs1 * user_embs2, -1)
        pos_ratings_item = torch.sum(item_embs1 * item_embs2, -1)
        tot_ratings_user = torch.matmul(user_embs1, torch.transpose(user_embeddings2, 0, 1))
        tot_ratings_item = torch.matmul(item_embs1, torch.transpose(item_embeddings2, 0, 1))
        ssl_logits_user = tot_ratings_user - pos_ratings_user[:, None]
        ssl_logits_item = tot_ratings_item - pos_ratings_item[:, None]
        bpr_loss = -torch.sum(F.logsigmoid(sup_logits))
        reg_loss = sum(torch.sum(w ** 2) / 2 for w in (raw_u, raw_p, raw_n))
        clogits_user = torch.logsumexp(ssl_logits_user / tau, dim=1)
        clogits_item = torch.logsumexp(ssl_logits_item / tau, dim=1)
        infonce_loss = torch.sum(clogits_user + clogits_item)
        theirs = bpr_loss + ssl_reg * infonce_loss + reg * reg_loss
        assert torch.allclose(mine, theirs, rtol=1e-5, atol=1e-4), (ssl_reg, tau, reg, mine.item(), theirs.item())
    print("ok  loss identical to the authors' lines (BPR sum + ssl_reg x InfoNCE sum + reg x L2) at 3 settings")


def run(args, cwd):
    out = subprocess.run(PY + args, cwd=cwd, capture_output=True, text=True, env=ENV)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]


def test_end_to_end():
    root = tempfile.mkdtemp(prefix="sgl_test_")
    make_dataset(os.path.join(root, "data/tiny"), 4, n_users=60)
    common = ["--data", "data/tiny", "--lr", "0.005", "--reg", "0.0001", "--epochs", "5", "--patience", "10",
              "--seed", "1", "--device", "cpu"]
    run(["rq1kit.sgl", "--ssl_reg", "0", "--ssl_ratio", "0", *common, "--run_dir", "runs/off", "--no_export"], root)
    run(["rq1kit.backbone", "--loss", "bpr", "--model", "lightgcn", *common, "--run_dir", "runs/plain", "--no_export"], root)
    h1 = [json.loads(x)["valid_clean_ndcg@20"] for x in open(f"{root}/runs/off/history.jsonl")]
    h2 = [json.loads(x)["valid_clean_ndcg@20"] for x in open(f"{root}/runs/plain/history.jsonl")]
    assert len(h1) == 5 and np.allclose(h1, h2, atol=5e-3), (h1, h2)
    print("ok  SGL with the contrastive weight 0 follows Plain-BPR:", [round(x, 4) for x in h1], "vs", [round(x, 4) for x in h2])
    run(["rq1kit.sgl", "--ssl_reg", "0.1", "--ssl_ratio", "0.2", "--ssl_temp", "0.2", *common, "--train_file", "train_N2_20_s1.tsv",
         "--run_dir", "runs/sgl"], root)
    run(["rq1kit.evaluate", "--data", "data/tiny", "--train_file", "train_N2_20_s1.tsv", "--topk", "runs/sgl/topk_test.npy",
         "--out", "results/sgl.json", "--tag", "method=SGL"], root)
    r = json.load(open(f"{root}/results/sgl.json"))
    assert r["seen_item_leak_rate"] == 0
    print(f"ok  SGL end to end on injected noise: test NDCG@20 {r['ndcg@20']:.4f}, leak 0")


if __name__ == "__main__":
    test_subgraph()
    test_loss_matches_authors()
    test_end_to_end()
    print("ALL SGL TESTS PASSED")
