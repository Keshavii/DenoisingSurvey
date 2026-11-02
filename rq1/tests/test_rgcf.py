"""Tests for the RGCF adapter (rq1kit/rgcf.py). CPU, about a minute.

  cd ~/rq1-kit && python tests/test_rgcf.py [path to the authors' RGCF repository]

1. The adapter's loss, denoised graph and augmented graph equal the authors' RGCF class (rgcf.py of the authors'
   repository, run as published with the RecBole base classes replaced by minimal stand-ins; skipped with a notice if
   the repository is absent), on the same parameters, the same batch and the same random augmentation pool,
   at three settings.
2. With the pruning threshold 0 and the contrastive weight 0 the loss is the authors' BPR + norm penalty only.
3. End to end on a tiny dataset: trains, exports top-K lists with no seen-item leak, two runs with the same seed give
   identical validation scores, the grid has the keys the adapter accepts.
"""
import json
import os
import subprocess
import sys
import tempfile
import types

import numpy as np
import scipy.sparse as sp
import torch
import torch.nn as nn

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT)
sys.path.insert(0, os.path.join(KIT, "tests"))
from rq1kit.rgcf import RGCF, rgcf_loss  # noqa: E402
from test_partc import make_dataset  # noqa: E402

PY = [sys.executable, "-m"]
ENV = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONPATH": KIT}
AUTHORS = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/repos/RGCF")
if not os.path.isdir(AUTHORS):
    AUTHORS = "/home/claude/ext/rgcf"


def load_authors():
    """Authors' rgcf.py with the RecBole classes it inherits from replaced by stand-ins of the same behaviour."""
    class GeneralRecommender(nn.Module):
        def __init__(self, config, dataset):
            super().__init__()
            self.USER_ID, self.ITEM_ID, self.NEG_ITEM_ID, self.RATING = "u", "i", "neg", "r"
            self.n_users, self.n_items, self.device = dataset.n_users, dataset.n_items, config["device"]

    class BPRLoss(nn.Module):  # RecBole 1.0.0
        def __init__(self, gamma=1e-10):
            super().__init__()
            self.gamma = gamma

        def forward(self, pos, neg):
            return -torch.log(self.gamma + torch.sigmoid(pos - neg)).mean()

    class EmbLoss(nn.Module):  # RecBole 1.0.0
        def __init__(self, norm=2):
            super().__init__()
            self.norm = norm

        def forward(self, *embeddings):
            emb_loss = torch.zeros(1)
            for e in embeddings:
                emb_loss += torch.norm(e, p=self.norm)
            return emb_loss / embeddings[-1].shape[0]

    def mod(name, **kw):
        m = types.ModuleType(name)
        m.__dict__.update(kw)
        sys.modules[name] = m
        return m
    for n in ("recbole", "recbole.model"):
        mod(n)
    mod("recbole.model.abstract_recommender", GeneralRecommender=GeneralRecommender)
    mod("recbole.model.init", xavier_uniform_initialization=lambda m: None)
    mod("recbole.model.loss", BPRLoss=BPRLoss, EmbLoss=EmbLoss)
    mod("recbole.utils", InputType=types.SimpleNamespace(PAIRWISE=0))
    src = open(os.path.join(AUTHORS, "utils.py")).read()
    ns = {}
    exec("import scipy.sparse as sp\nimport torch\n" + src[src.index("def sp2tensor"):src.index("def del_tensor_ele")], ns)
    mod("utils", sp2tensor=ns["sp2tensor"])
    if not hasattr(sp.dok_matrix, "_update"):  # the authors' code targets scipy 1.7; same operation in current scipy
        sp.dok_matrix._update = sp.dok_matrix.update
    sys.path.insert(0, AUTHORS)
    import importlib
    return importlib.import_module("rgcf")


class Cfg(dict):
    pass


def make_graph(nu=30, ni=40, n=300, seed=0):
    rng = np.random.default_rng(seed)
    pairs = np.unique(np.stack([rng.integers(0, nu, n), rng.integers(0, ni, n)], 1), axis=0)
    return nu, ni, pairs[:, 0], pairs[:, 1]


def test_matches_authors():
    if not os.path.isfile(os.path.join(AUTHORS, "rgcf.py")):
        print("skip  authors' repository not found, comparison not run")
        return
    A = load_authors()
    nu, ni, users, items = make_graph()
    ds = types.SimpleNamespace(n_users=nu, n_items=ni,
                               inter_matrix=lambda form, value_field: sp.coo_matrix((np.ones(len(users)), (users, items)), shape=(nu, ni)))
    for prune, mim, tau, aug in ((0.02, 1e-6, 0.2, 0.1), (0.06, 1e-5, 0.1, 0.2), (0.0, 0.0, 0.2, 0.1)):
        cfg = Cfg(embedding_size=16, n_layers=2, reg_weight=1e-5, inter_matrix_type="01", spmm="off", prune_threshold=prune,
                  MIM_weight=mim, tau=tau, aug_ratio=aug, device="cpu")
        theirs = A.RGCF(cfg, ds)
        theirs.special_spmm = torch.sparse.mm
        mine = RGCF(nu, ni, users, items, 16, 2, prune, tau, aug, "cpu")
        with torch.no_grad():
            mine.user_linear.weight.copy_(theirs.user_linear.weight)
            mine.item_linear.weight.copy_(theirs.item_linear.weight)
        g = torch.Generator().manual_seed(5)
        B = 24
        u = torch.randint(0, nu, (B,), generator=g)
        p = torch.randint(0, ni, (B,), generator=g)
        n = torch.randint(0, ni, (B,), generator=g)
        # the authors' denoised graph and embeddings
        U1, I1 = theirs.forward(pruning=prune)
        U2, I2 = mine.forward(prune)
        assert torch.allclose(U1, U2, atol=1e-5) and torch.allclose(I1, I2, atol=1e-5), (prune, "embeddings differ")
        # the same random augmentation pool for both
        pool = int(theirs.adj._nnz() * aug * 0.5 * theirs.pool_multi)
        au, ai = torch.randint(0, nu, (pool,), generator=g), torch.randint(0, ni, (pool,), generator=g)
        calls = iter([au.numpy(), ai.numpy()])
        real = np.random.choice
        np.random.choice = lambda *a_, **k_: next(calls)
        try:
            l_theirs = theirs.calculate_loss({"u": u, "i": p, "neg": n}, 0, None)
        finally:
            np.random.choice = real
        if mim > 0:  # the augmented graph itself, on the same pool
            calls2 = iter([au.numpy(), ai.numpy()])
            np.random.choice = lambda *a_, **k_: next(calls2)
            try:
                their_aug = theirs.get_aug_adj(theirs.adj.detach()).to_dense()
            finally:
                np.random.choice = real
            assert torch.allclose(their_aug, mine.aug_adj(au, ai).to_dense(), atol=1e-6), (prune, "augmented graph differs")
        l_mine = rgcf_loss(mine, u, p, n, 1e-5, mim, au, ai)
        assert torch.allclose(l_theirs.reshape(()), l_mine, rtol=1e-4, atol=1e-6), (prune, mim, l_theirs.item(), l_mine.item())
        l_theirs.reshape(()).backward()
        l_mine.backward()
        gd = (theirs.user_linear.weight.grad - mine.user_linear.weight.grad).abs().max().item()
        print("   setting", prune, mim, "max grad diff", gd, "max grad", theirs.user_linear.weight.grad.abs().max().item())
        assert gd <= 1e-3 * theirs.user_linear.weight.grad.abs().max().item() + 1e-9, "gradients differ"  # float32 noise only
    print("ok  denoised graph, augmented graph, embeddings, loss and gradients identical to the authors' RGCF (3 settings)")


def run(args, cwd):
    out = subprocess.run(PY + args, cwd=cwd, capture_output=True, text=True, env=ENV)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]


def test_end_to_end():
    root = tempfile.mkdtemp(prefix="rgcf_test_")
    make_dataset(os.path.join(root, "data/tiny"), 4, n_users=60)
    common = ["--data", "data/tiny", "--lr", "0.005", "--lr_mult", "2", "--epochs", "4", "--patience", "10", "--seed", "1",
              "--device", "cpu", "--batch", "64", "--dim", "16", "--layers", "2"]
    run(["rq1kit.rgcf", *common, "--train_file", "train_N2_20_s1.tsv", "--run_dir", "runs/a"], root)
    run(["rq1kit.rgcf", *common, "--train_file", "train_N2_20_s1.tsv", "--run_dir", "runs/b", "--no_export"], root)
    info = json.load(open(f"{root}/runs/a/run.json"))
    assert abs(info["lr_effective"] - 0.01) < 1e-12, info
    ha = [json.loads(x) for x in open(f"{root}/runs/a/history.jsonl")]
    hb = [json.loads(x) for x in open(f"{root}/runs/b/history.jsonl")]
    assert len(ha) == 4 and all(x["valid_clean_ndcg@20"] == y["valid_clean_ndcg@20"] for x, y in zip(ha, hb)), (ha, hb)
    run(["rq1kit.evaluate", "--data", "data/tiny", "--train_file", "train_N2_20_s1.tsv", "--topk", "runs/a/topk_test.npy",
         "--out", "results/rgcf.json", "--tag", "method=RGCF"], root)
    r = json.load(open(f"{root}/results/rgcf.json"))
    assert r["seen_item_leak_rate"] == 0
    grid = json.load(open(os.path.join(KIT, "configs/partc/methods/rgcf.json")))["grid"]
    assert len(grid) == 8 and all(set(g) == {"lr_mult", "prune_threshold", "MIM_weight"} for g in grid)
    print(f"ok  end to end: lr 0.005 x 2 = 0.01, reruns identical, test NDCG@20 {r['ndcg@20']:.4f}, no leak, grid keys valid")


def test_edge_spmm():
    """EdgeSpMM equals torch.sparse.mm (forward bitwise, gradients of values and inputs to 1e-6) and its backward never
    builds an n x n matrix: 4000 x 4000 nodes would need 64 MB dense, so we only check numbers here, memory is by design."""
    from rq1kit.rgcf import EdgeSpMM, sparse_sorted
    torch.manual_seed(0)
    n, dim, nnz = 200, 8, 900
    pairs = torch.unique(torch.randint(0, n, (2, nnz)), dim=1)
    order = torch.argsort(pairs[0] * n + pairs[1])
    rows, cols = pairs[0][order], pairs[1][order]
    vals0 = torch.rand(len(rows))
    x0 = torch.randn(n, dim)
    w = torch.randn(n, dim)
    v1, x1 = vals0.clone().requires_grad_(), x0.clone().requires_grad_()
    out1 = EdgeSpMM.apply(v1, x1, rows, cols, n)
    (out1 * w).sum().backward()
    v2, x2 = vals0.clone().requires_grad_(), x0.clone().requires_grad_()
    out2 = torch.sparse.mm(sparse_sorted(torch.stack([rows, cols]), v2, (n, n)), x2)
    (out2 * w).sum().backward()
    assert torch.equal(out1, out2), "forward must be bitwise identical"
    assert torch.allclose(v1.grad, v2.grad, atol=1e-6) and torch.allclose(x1.grad, x2.grad, atol=1e-6)
    print("ok  EdgeSpMM equals torch.sparse.mm: forward bitwise, gradients to 1e-6")


if __name__ == "__main__":
    test_edge_spmm()
    test_matches_authors()
    test_end_to_end()
    print("ALL RGCF TESTS PASSED")
