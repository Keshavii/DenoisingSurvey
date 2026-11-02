"""Tests for the DDRM adapter (rq1kit/ddrm.py). CPU, about a minute.

  cd ~/rq1-kit && python tests/test_ddrm.py [path to the authors' DDRM repository]

1. Against the authors' DDRM_LightGCN code (model.DNN, diffusion.GaussianDiffusion, model.LightGCN.bpr_loss /
   computer_infer / rounding_inner, utils.BPRLoss.call_bpr's loss composition; imported as published): the conditional DNN,
   the noise schedule and the conditional reverse step (including time steps beyond the schedule), the training loss and its
   gradients for both networks (beta 0 and 0.5), and the inference scores. Skipped with a notice if the repository is absent.
2. End to end on a tiny dataset: pretrains and caches the LightGCN, trains, exports top-K lists with no seen-item leak,
   identical reruns, grid keys valid.
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import scipy.sparse as sp
import torch

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT)
sys.path.insert(0, os.path.join(KIT, "tests"))
from rq1kit import diffrec as D  # noqa: E402
from rq1kit.backbone import Backbone, norm_adj  # noqa: E402
from rq1kit.ddrm import CondDiffusion, CondDNN, ddrm_loss, ddrm_scores  # noqa: E402
from test_partc import make_dataset  # noqa: E402

PY = [sys.executable, "-m"]
ENV = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONPATH": KIT}
AUTHORS = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/repos/DDRM")
if not os.path.isdir(AUTHORS):
    AUTHORS = "/home/claude/ext/DDRM"


def test_matches_authors():
    code = os.path.join(AUTHORS, "DDRM_LightGCN")
    if not os.path.isfile(os.path.join(code, "diffusion.py")):
        print("skip  authors' repository not found, comparison not run")
        return
    cwd = os.getcwd()
    argv = sys.argv[:]
    os.chdir(code)
    sys.path.insert(0, code)
    sys.argv = ["x", "--act", "relu", "--steps", "5"]
    try:
        import diffusion as AD
        import model as AM
        import world
    finally:
        os.chdir(cwd)
        sys.argv = argv
    dev = torch.device("cpu")
    nu, ni, d = 30, 40, 8
    rng = np.random.default_rng(0)
    pairs = np.unique(np.stack([rng.integers(0, nu, 300), rng.integers(0, ni, 300)], 1), axis=0)
    csr = sp.csr_matrix((np.ones(len(pairs), dtype=np.float32), (pairs[:, 0], pairs[:, 1])), shape=(nu, ni))
    adj = norm_adj(csr, dev)
    bb = Backbone(nu, ni, d, "lightgcn", 2, adj)

    class DS:
        n_users, m_items = nu, ni

        def getSparseGraph(self):
            return adj

    world.config.update(latent_dim_rec=d, lightGCN_n_layers=2, dropout=0, keep_prob=0.6, A_split=False, pretrain=0,
                        steps=5, sampling_steps=7, sampling_noise=False)
    for act in ("relu", "tanh"):
        world.config["act"] = act
        out_dims, in_dims = [16, 24, d], [d, 24, 16]
        out_dims = [16, 24] + [d]
        in_dims = out_dims[::-1]
        torch.manual_seed(1)
        a = AM.DNN(in_dims, out_dims, 6, "cat", False)
        b = CondDNN(in_dims, out_dims, 6, act)
        b.load_state_dict(a.state_dict())
        a.eval(); b.eval()
        x, c, t = torch.randn(12, d), torch.randn(12, d), torch.randint(0, 5, (12,))
        assert torch.allclose(a(x, c, t), b(x, c, t), atol=1e-6), act
    ad = AD.GaussianDiffusion(world.config, AD.ModelMeanType.START_X, "linear-var", 1e-2, 1e-4, 1e-3, 5, dev)
    bd = CondDiffusion(D.ModelMeanType.START_X, "linear-var", 1e-2, 1e-4, 1e-3, 5, dev)
    for k in ("betas", "alphas_cumprod", "posterior_variance", "posterior_log_variance_clipped", "posterior_mean_coef1", "posterior_mean_coef2"):
        assert torch.equal(getattr(ad, k), getattr(bd, k)), k
    t_beyond = torch.tensor([7] * 12)
    oa = ad.p_mean_variance(a, x, c, t_beyond)
    ob = bd.p_mean_variance(b, x, c, t_beyond)
    for k in ("mean", "variance", "log_variance"):
        assert torch.allclose(oa[k], ob[k], atol=1e-6), k
    world.config["act"] = "relu"  # the authors' DNN reads the activation from the config at every forward

    # the training loss: authors' LightGCN.bpr_loss + BPRLoss.call_bpr composition
    lg = AM.LightGCN(world.config, DS())
    lg.embedding_user.weight.data.copy_(bb.user.weight)
    lg.embedding_item.weight.data.copy_(bb.item.weight)
    g = torch.Generator().manual_seed(4)
    B = 20
    u = torch.randint(0, nu, (B,), generator=g)
    p = torch.randint(0, ni, (B,), generator=g)
    n = torch.randint(0, ni, (B,), generator=g)
    for alpha, beta, decay in ((0.1, 0.0, 0.0), (0.5, 0.5, 1e-4)):
        torch.manual_seed(2)
        ur_a, ir_a = AM.DNN(in_dims, out_dims, 6, "cat", False), AM.DNN(in_dims, out_dims, 6, "cat", False)
        ur_b, ir_b = CondDNN(in_dims, out_dims, 6), CondDNN(in_dims, out_dims, 6)
        ur_b.load_state_dict(ur_a.state_dict()); ir_b.load_state_dict(ir_a.state_dict())
        torch.manual_seed(9)
        loss, reg_loss, re_loss, pos_score = lg.bpr_loss(u, p, n, ur_a, ir_a, ad)
        loss = loss + reg_loss * decay
        weight = torch.pow(torch.sigmoid(pos_score).detach(), beta)
        theirs = ((1 - alpha) * loss + alpha * re_loss) * weight
        theirs = theirs.mean()
        ga = torch.autograd.grad(theirs, list(ur_a.parameters()) + list(ir_a.parameters()), allow_unused=True)
        torch.manual_seed(9)
        U, I = bb.propagate()
        mine = ddrm_loss(U, I, bb.user(u), bb.item(p), bb.item(n), u, p, n, ur_b, ir_b, bd, alpha, beta, decay)
        gb = torch.autograd.grad(mine, list(ur_b.parameters()) + list(ir_b.parameters()), allow_unused=True)
        assert torch.allclose(theirs, mine, rtol=1e-5, atol=1e-7), (alpha, beta, theirs.item(), mine.item())
        for x_, y_ in zip(ga, gb):
            if x_ is None:
                assert y_ is None or y_.abs().max() == 0
            else:
                assert (x_ - y_).abs().max().item() <= 1e-4 * x_.abs().max().item() + 1e-9, "gradients differ"

    # inference
    ur_a.eval(); ir_a.eval(); ir_b.eval()
    users = torch.arange(0, nu, 3)
    all_pos = [csr[int(x)].nonzero()[1] for x in users]
    torch.manual_seed(11)
    item_emb, all_items = lg.computer_infer(users, all_pos, ad, ur_a, ir_a)
    theirs = lg.rounding_inner(item_emb, all_items)
    torch.manual_seed(11)
    U, I = bb.propagate()
    mine = ddrm_scores(U, I, users, csr, ir_b, bd, 7, dev)
    assert torch.allclose(theirs, mine, rtol=1e-4, atol=1e-6), (theirs - mine).abs().max()
    print("ok  DNN, schedule, conditional reverse step (also beyond the schedule), training loss + gradients (2 settings), inference scores identical to the authors' DDRM")


def run(args, cwd):
    out = subprocess.run(PY + args, cwd=cwd, capture_output=True, text=True, env=ENV)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]


def test_end_to_end():
    root = tempfile.mkdtemp(prefix="ddrm_test_")
    make_dataset(os.path.join(root, "data/tiny"), 4, n_users=60)
    common = ["--data", "data/tiny", "--model", "lightgcn", "--lr", "0.005", "--reg", "0.0001", "--epochs", "6", "--eval_every", "2",
              "--seed", "1", "--device", "cpu", "--batch", "64", "--dim", "16", "--layers", "2", "--dnn_dims", "[32]", "--steps", "5",
              "--pre_epochs", "5", "--pre_patience", "3", "--diff_lr", "0.001"]
    run(["rq1kit.ddrm", *common, "--train_file", "train_N2_20_s1.tsv", "--run_dir", "runs/a"], root)
    assert len(os.listdir(f"{root}/runs/_ddrm_pretrain")) == 1
    run(["rq1kit.ddrm", *common, "--train_file", "train_N2_20_s1.tsv", "--run_dir", "runs/b", "--no_export"], root)
    assert len(os.listdir(f"{root}/runs/_ddrm_pretrain")) == 1, "pretraining was not reused"
    ha = [json.loads(x) for x in open(f"{root}/runs/a/history.jsonl")]
    hb = [json.loads(x) for x in open(f"{root}/runs/b/history.jsonl")]
    assert len(ha) == 3 and all(x["valid_clean_ndcg@20"] == y["valid_clean_ndcg@20"] for x, y in zip(ha, hb)), (ha, hb)
    run(["rq1kit.evaluate", "--data", "data/tiny", "--train_file", "train_N2_20_s1.tsv", "--topk", "runs/a/topk_test.npy",
         "--out", "results/ddrm.json", "--tag", "method=DDRM"], root)
    r = json.load(open(f"{root}/results/ddrm.json"))
    assert r["seen_item_leak_rate"] == 0
    grid = json.load(open(os.path.join(KIT, "configs/partc/methods/ddrm.json")))["grid"]
    assert len(grid) == 8 and all(set(x) == {"diff_lr", "alpha", "steps"} for x in grid)
    print(f"ok  end to end: pretraining cached and reused, reruns identical, test NDCG@20 {r['ndcg@20']:.4f}, no leak, grid keys valid")


if __name__ == "__main__":
    test_matches_authors()
    test_end_to_end()
    print("ALL DDRM TESTS PASSED")
