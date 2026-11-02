"""Tests for the DiffRec adapter (rq1kit/diffrec.py). CPU, about a minute.

  cd ~/rq1-kit && python tests/test_diffrec.py [path to the authors' DiffRec repository]

1. The adapter's GaussianDiffusion and DNN equal the authors' (models/gaussian_diffusion.py, models/DNN.py of
   YiyanXu/DiffRec, loaded as published): beta schedules and derived tables; over 40 training batches (enough to switch
   from uniform to importance sampling of the time steps) the losses, the importance-sampler loss history and the
   parameter updates agree, for mean type x0 and eps; p_sample outputs agree with and without sampling noise.
   Skipped with a notice if the repository is absent.
2. valid_ndcg_scores equals rq1kit.backbone.valid_ndcg on a LightGCN-like model.
3. End to end on a tiny dataset: trains, exports top-K lists with no seen-item leak, identical reruns, grid keys valid.
"""
import importlib.util
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
from rq1kit.backbone import Backbone, norm_adj, valid_ndcg  # noqa: E402
from rq1kit.dense import valid_ndcg_scores  # noqa: E402
from test_partc import make_dataset  # noqa: E402

PY = [sys.executable, "-m"]
ENV = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONPATH": KIT}
AUTHORS = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/repos/DiffRec")
if not os.path.isdir(AUTHORS):
    AUTHORS = "/home/claude/ext/DiffRec"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_matches_authors():
    base = os.path.join(AUTHORS, "DiffRec", "models")
    if not os.path.isfile(os.path.join(base, "gaussian_diffusion.py")):
        print("skip  authors' repository not found, comparison not run")
        return
    GD, DNN = load(os.path.join(base, "gaussian_diffusion.py"), "authors_gd"), load(os.path.join(base, "DNN.py"), "authors_dnn")
    dev = torch.device("cpu")
    n_item = 50
    for sched, scale, steps in (("linear-var", 1e-3, 5), ("linear", 0.1, 8), ("cosine", 0.1, 6)):
        a = GD.GaussianDiffusion(GD.ModelMeanType.START_X, sched, scale, 1e-3, 1e-2, steps, dev)
        b = D.GaussianDiffusion(D.ModelMeanType.START_X, sched, scale, 1e-3, 1e-2, steps, dev)
        for k in ("betas", "alphas_cumprod", "posterior_variance", "posterior_log_variance_clipped", "posterior_mean_coef1",
                  "posterior_mean_coef2", "sqrt_recipm1_alphas_cumprod"):
            assert torch.equal(getattr(a, k), getattr(b, k)), (sched, k)
    for mean_type_a, mean_type_b in ((GD.ModelMeanType.START_X, D.ModelMeanType.START_X),
                                     (GD.ModelMeanType.EPSILON, D.ModelMeanType.EPSILON)):
        torch.manual_seed(0)
        dn_a = DNN.DNN([n_item, 20], [20, n_item], 6, "cat", False)
        dn_b = D.DNN([n_item, 20], [20, n_item], 6, "cat", False)
        dn_b.load_state_dict(dn_a.state_dict())
        ga = GD.GaussianDiffusion(mean_type_a, "linear-var", 0.1, 1e-3, 1e-2, 5, dev)
        gb = D.GaussianDiffusion(mean_type_b, "linear-var", 0.1, 1e-3, 1e-2, 5, dev)
        oa = torch.optim.AdamW(dn_a.parameters(), lr=1e-3)
        ob = torch.optim.AdamW(dn_b.parameters(), lr=1e-3)
        data = (torch.rand(32, n_item) < 0.2).float()
        for it in range(40):
            torch.manual_seed(100 + it)
            la = ga.training_losses(dn_a, data, True)["loss"].mean()
            torch.manual_seed(100 + it)
            lb = gb.training_losses(dn_b, data, True)["loss"].mean()
            assert torch.allclose(la, lb, rtol=1e-6, atol=1e-9), (it, la.item(), lb.item())
            oa.zero_grad(); la.backward(); oa.step()
            ob.zero_grad(); lb.backward(); ob.step()
        assert (ga.Lt_count == gb.Lt_count).all() and np.allclose(ga.Lt_history.numpy(), gb.Lt_history, rtol=1e-6)
        assert (gb.Lt_count == gb.history_num_per_term).all(), "importance branch not reached"
        for pa, pb in zip(dn_a.parameters(), dn_b.parameters()):
            assert torch.allclose(pa, pb, rtol=1e-5, atol=1e-8), "parameters differ after training"
        dn_a.eval(); dn_b.eval()
        for noise in (False, True):
            torch.manual_seed(5)
            xa = ga.p_sample(dn_a, data, 2, noise)
            torch.manual_seed(5)
            xb = gb.p_sample(dn_b, data, 2, noise)
            assert torch.allclose(xa, xb, rtol=1e-5, atol=1e-7)
    print("ok  schedules, 40 training batches (losses, importance-sampler history, parameters) and p_sample identical to the authors' DiffRec, x0 and eps")


def test_valid_helper():
    rng = np.random.default_rng(0)
    nu, ni = 40, 50
    pairs = np.unique(np.stack([rng.integers(0, nu, 400), rng.integers(0, ni, 400)], 1), axis=0)
    tr = sp.csr_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(nu, ni))
    pv = np.unique(np.stack([rng.integers(0, nu, 100), rng.integers(0, ni, 100)], 1), axis=0)
    va = sp.csr_matrix((np.ones(len(pv)), (pv[:, 0], pv[:, 1])), shape=(nu, ni))
    model = Backbone(nu, ni, 8, "lightgcn", 2, norm_adj(tr, torch.device("cpu")))
    U, I = model.propagate()
    r1 = valid_ndcg(model, tr, {"valid_clean": va}, torch.device("cpu"), batch=16)
    r2 = valid_ndcg_scores(lambda users: U[users] @ I.T, nu, tr, {"valid_clean": va}, torch.device("cpu"), batch=16)
    assert abs(r1["valid_clean"] - r2["valid_clean"]) < 1e-9, (r1, r2)
    print("ok  valid_ndcg_scores equals the kit's valid_ndcg")


def run(args, cwd):
    out = subprocess.run(PY + args, cwd=cwd, capture_output=True, text=True, env=ENV)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]


def test_end_to_end():
    root = tempfile.mkdtemp(prefix="diffrec_test_")
    make_dataset(os.path.join(root, "data/tiny"), 4, n_users=60)
    common = ["--data", "data/tiny", "--model", "lightgcn", "--lr", "0.005", "--reg", "0.0001", "--epochs", "10", "--eval_every", "2",
              "--seed", "1", "--device", "cpu", "--batch_size", "16", "--dims", "[32]", "--steps", "5", "--diff_lr", "0.001"]
    run(["rq1kit.diffrec", *common, "--train_file", "train_N2_20_s1.tsv", "--run_dir", "runs/a"], root)
    run(["rq1kit.diffrec", *common, "--train_file", "train_N2_20_s1.tsv", "--run_dir", "runs/b", "--no_export"], root)
    ha = [json.loads(x) for x in open(f"{root}/runs/a/history.jsonl")]
    hb = [json.loads(x) for x in open(f"{root}/runs/b/history.jsonl")]
    assert len(ha) >= 2 and all(x["valid_clean_ndcg@20"] == y["valid_clean_ndcg@20"] for x, y in zip(ha, hb)), (ha, hb)
    run(["rq1kit.evaluate", "--data", "data/tiny", "--train_file", "train_N2_20_s1.tsv", "--topk", "runs/a/topk_test.npy",
         "--out", "results/diffrec.json", "--tag", "method=DiffRec"], root)
    r = json.load(open(f"{root}/results/diffrec.json"))
    assert r["seen_item_leak_rate"] == 0
    grid = json.load(open(os.path.join(KIT, "configs/partc/methods/diffrec.json")))["grid"]
    assert len(grid) == 8 and all(set(x) == {"diff_lr", "noise_scale", "steps"} for x in grid)
    print(f"ok  end to end: reruns identical, test NDCG@20 {r['ndcg@20']:.4f}, no leak, grid keys valid")


if __name__ == "__main__":
    test_matches_authors()
    test_valid_helper()
    test_end_to_end()
    print("ALL DIFFREC TESTS PASSED")
