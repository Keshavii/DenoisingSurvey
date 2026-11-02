"""Tests for the BOD adapter (rq1kit/bod.py). CPU, about a minute.

  cd ~/rq1-kit && python tests/test_bod.py [path to the authors' BOD repository]

1. Inner loss (weighted BPR + alignment + uniformity), the generator, and the outer gradient-matching loss equal the
   authors' functions (util/loss_torch.py, match_loss, distance_wb, GraphGenerator_VAE of model/graph/BOD.py, run as
   published; 'cuda' replaced by 'cpu' in match_loss), on the same inputs: values, and gradients w.r.t. the recommender's
   embeddings (inner) and the generator's weights (outer, second order through LightGCN propagation).
   Skipped with a notice if the repository is absent.
2. End to end on a tiny dataset: trains, exports top-K lists with no seen-item leak, reruns with the same seed give
   identical validation scores, the grid has the keys the adapter accepts.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

import torch
import torch.nn as nn

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT)
sys.path.insert(0, os.path.join(KIT, "tests"))
from rq1kit.backbone import Backbone  # noqa: E402
from rq1kit.bod import Generator, inner_loss, outer_loss  # noqa: E402
from test_partc import make_dataset  # noqa: E402

PY = [sys.executable, "-m"]
ENV = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONPATH": KIT}
AUTHORS = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/repos/BOD")
if not os.path.isdir(AUTHORS):
    AUTHORS = "/home/claude/ext/BOD"


def load_authors():
    spec = importlib.util.spec_from_file_location("bod_loss", os.path.join(AUTHORS, "util", "loss_torch.py"))
    L = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(L)
    src = open(os.path.join(AUTHORS, "model/graph/BOD.py")).read().replace("'cuda'", "'cpu'")
    ns = {"torch": torch, "nn": nn}
    exec(src[src.index("def match_loss"):src.index("class BOD(")], ns)
    exec("import torch.nn as nn\nimport torch\n" + src[src.index("class GraphGenerator_VAE"):], ns)
    return L, ns


def test_matches_authors():
    if not os.path.isfile(os.path.join(AUTHORS, "model/graph/BOD.py")):
        print("skip  authors' repository not found, comparison not run")
        return
    L, ns = load_authors()
    nu, ni, d, B = 30, 40, 16, 24
    import numpy as np
    import scipy.sparse as sp
    rng = np.random.default_rng(0)
    pairs = np.unique(np.stack([rng.integers(0, nu, 300), rng.integers(0, ni, 300)], 1), axis=0)
    from rq1kit.backbone import norm_adj
    adj = norm_adj(sp.csr_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(nu, ni)), torch.device("cpu"))
    model = Backbone(nu, ni, d, "lightgcn", 2, adj)
    theirs_gen = ns["GraphGenerator_VAE"](None, d)
    mine_gen = Generator(d)
    with torch.no_grad():
        for n_ in ("encoder", "fc_encoder", "fc_decode"):
            getattr(mine_gen, n_).weight.copy_(getattr(theirs_gen, n_).weight)
            getattr(mine_gen, n_).bias.copy_(getattr(theirs_gen, n_).bias)
    g = torch.Generator().manual_seed(3)
    u = torch.randint(0, nu, (B,), generator=g)
    p = torch.randint(0, ni, (B,), generator=g)
    n = torch.randint(0, ni, (B,), generator=g)
    x = torch.randn(B, d, generator=g)
    y = torch.randn(B, d, generator=g)
    assert torch.allclose(theirs_gen(x, y), mine_gen(x, y), atol=1e-7), "generator differs"

    for wb, wa, wu in ((1.0, 1.0, 0.5), (0.7, 1.3, 1.0)):
        # inner loss: values and gradients w.r.t. the embedding tables
        U, I = model.propagate()
        mine = inner_loss(U[u], I[p], I[n], mine_gen, wb, wa, wu)
        gm = torch.autograd.grad(mine, list(model.parameters()))
        U, I = model.propagate()
        eu, ep, en = U[u], I[p], I[n]
        wpos, wneg = theirs_gen(eu, ep).detach(), theirs_gen(eu, en).detach()
        uni = (L.uniformity_loss(eu) + L.uniformity_loss(eu) + L.uniformity_loss(ep) + L.uniformity_loss(en)) / 4
        theirs = wb * L.bpr_loss_weight(eu, ep, en, wpos, wneg) + wa * L.alignment_loss_weight_1(eu, ep, wpos) + wu * uni
        gt = torch.autograd.grad(theirs, list(model.parameters()))
        assert torch.allclose(mine, theirs, rtol=1e-5, atol=1e-7), (mine.item(), theirs.item())
        for a_, b_ in zip(gm, gt):
            assert (a_ - b_).abs().max().item() <= 1e-5 * b_.abs().max().item() + 1e-9, "inner gradients differ"

    # outer loss: value, and gradient w.r.t. the generator's weights (second order)
    params = list(model.parameters())
    U, I = model.propagate()
    eu, ep, en = U[u], I[p], I[n]
    mine, _, _ = outer_loss(params, eu, ep, en, mine_gen, 1e-3)
    gm = torch.autograd.grad(mine, list(mine_gen.parameters()), allow_unused=True)
    U, I = model.propagate()
    eu, ep, en = U[u], I[p], I[n]
    wr_pos, wr_neg = theirs_gen(eu, eu), theirs_gen(eu, en)
    bpr_ol = L.bpr_loss_weight(eu, ep, en, wr_pos, wr_neg)
    gw_real = torch.autograd.grad(bpr_ol, params, retain_graph=True, create_graph=True)
    align_ol = L.alignment_loss_weight_1(eu, ep, theirs_gen(eu, ep))
    gw_syn = torch.autograd.grad(align_ol, params, retain_graph=True, create_graph=True)
    theirs = ns["match_loss"](gw_syn, gw_real, "ours")
    theirs = theirs + L.l2_reg_loss(1e-3, eu, ep)
    gt = torch.autograd.grad(theirs, list(theirs_gen.parameters()), allow_unused=True)
    assert torch.allclose(mine, theirs, rtol=1e-4, atol=1e-6), (mine.item(), theirs.item())
    for k, (a_, b_) in enumerate(zip(gm, gt)):
        if b_ is None:
            continue
        assert a_ is not None and (a_ - b_).abs().max().item() <= 1e-4 * b_.abs().max().item() + 1e-9, ("outer grad differs", k)
    print("ok  generator, inner loss + gradients, outer gradient-matching loss + second-order generator gradients identical to the authors'")


def run(args, cwd):
    out = subprocess.run(PY + args, cwd=cwd, capture_output=True, text=True, env=ENV)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]


def test_end_to_end():
    root = tempfile.mkdtemp(prefix="bod_test_")
    make_dataset(os.path.join(root, "data/tiny"), 4, n_users=60)
    common = ["--data", "data/tiny", "--lr", "0.005", "--lr_mult", "2", "--epochs", "4", "--patience", "10", "--seed", "1",
              "--device", "cpu", "--batch", "64", "--dim", "16"]
    run(["rq1kit.bod", *common, "--train_file", "train_N2_20_s1.tsv", "--run_dir", "runs/a"], root)
    run(["rq1kit.bod", *common, "--train_file", "train_N2_20_s1.tsv", "--run_dir", "runs/b", "--no_export"], root)
    info = json.load(open(f"{root}/runs/a/run.json"))
    assert abs(info["lr_effective"] - 0.01) < 1e-12, info
    ha = [json.loads(x) for x in open(f"{root}/runs/a/history.jsonl")]
    hb = [json.loads(x) for x in open(f"{root}/runs/b/history.jsonl")]
    assert len(ha) == 4 and all(x["valid_clean_ndcg@20"] == y["valid_clean_ndcg@20"] for x, y in zip(ha, hb)), (ha, hb)
    run(["rq1kit.evaluate", "--data", "data/tiny", "--train_file", "train_N2_20_s1.tsv", "--topk", "runs/a/topk_test.npy",
         "--out", "results/bod.json", "--tag", "method=BOD"], root)
    r = json.load(open(f"{root}/results/bod.json"))
    assert r["seen_item_leak_rate"] == 0
    grid = json.load(open(os.path.join(KIT, "configs/partc/methods/bod.json")))["grid"]
    assert len(grid) == 8 and all(set(g) == {"lr_mult", "generator_lr", "weight_uniformity"} for g in grid)
    print(f"ok  end to end: lr 0.005 x 2 = 0.01, reruns identical, test NDCG@20 {r['ndcg@20']:.4f}, no leak, grid keys valid")


if __name__ == "__main__":
    test_matches_authors()
    test_end_to_end()
    print("ALL BOD TESTS PASSED")
