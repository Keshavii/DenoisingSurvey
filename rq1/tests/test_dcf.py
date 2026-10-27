"""Tests for the DCF adapter (rq1kit/dcf.py). CPU, about a minute.

  cd ~/rq1-kit && python tests/test_dcf.py [path to the authors' DCF repository, default ~/repos/DCF]

1. --selftest: DCF with drop 0 and relabel 0 equals plain BCE; with relabel 0 and no bound it keeps T-CE's set.
2. The port's loss equals the authors' PLC_uncertain_discard (loss.py, run on CPU) on the same inputs: loss,
   running mean and the low-loss indices.
3. End to end on a tiny dataset: DCF with drop 0 and relabel 0 trains exactly like rq1kit.backbone --loss bce
   (same validation curve), and a normal DCF run exports top-K lists with no seen-item leak.
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
from rq1kit.dcf import dcf_loss  # noqa: E402
from test_partc import make_dataset  # noqa: E402

PY = [sys.executable, "-m"]
ENV = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONPATH": KIT}


def authors_function(repo):
    src = open(os.path.join(repo, "loss.py")).read().replace(".cuda()", "")
    ns = {}
    exec(compile(src, "DCF/loss.py (cuda calls removed)", "exec"), ns)
    return ns["PLC_uncertain_discard"]


def test_selftest():
    out = subprocess.run(PY + ["rq1kit.dcf", "--selftest"], cwd=KIT, capture_output=True, text=True, env=ENV)
    assert out.returncode == 0, out.stderr
    print("ok  " + out.stdout.strip())


def test_against_authors(repo):
    if not os.path.exists(os.path.join(repo, "loss.py")):
        print(f"SKIP authors' comparison: {repo}/loss.py not found")
        return
    plc = authors_function(repo)
    rng = np.random.default_rng(0)
    B, n_items = 600, 5000
    users = np.arange(B)
    pos_items = rng.integers(0, n_items, B)
    neg_items = (pos_items + 1 + rng.integers(0, n_items - 1, B)) % n_items
    train_mat = sp.dok_matrix((B, n_items), dtype=np.float32)
    for u, i in zip(users, pos_items):
        train_mat[u, i] = 1.0
    user = torch.tensor(np.concatenate([users, users]))
    item = torch.tensor(np.concatenate([pos_items, neg_items]))
    g = torch.Generator().manual_seed(1)
    pos, neg = torch.randn(B, generator=g) * 2, torch.randn(B, generator=g) * 2
    y = torch.cat([pos, neg])
    t = torch.cat([torch.ones(B), torch.zeros(B)])
    for epoch0, co, drop, relabel in [(0, 1e-4, 0.2, 0.05), (2, 0.01, 0.2, 0.09), (4, 0.1, 0.1, 0.27), (1, 0.0, 0.05, 0.0)]:
        before = np.abs(rng.normal(size=(2 * B, 1))) * (epoch0 > 0)
        sn = torch.from_numpy(rng.integers(1, 5, size=(2 * B, 1)).astype(np.float64))
        l_a, _, mean_a, low_a = plc(user, item, train_mat, y, t, drop, epoch0, sn, before, co, relabel)
        l_m, mean_m, low_m = dcf_loss(pos, neg, drop, epoch0 + 1, sn.squeeze(), torch.from_numpy(before).float().squeeze(), co, relabel)
        assert torch.allclose(l_m / 2, l_a.float(), atol=1e-6), (l_m / 2, l_a)
        assert torch.allclose(mean_m.float(), mean_a.float(), atol=1e-6)
        assert np.array_equal(low_m.numpy(), np.asarray(low_a)), "low-loss indices differ"
    print("ok  port equals the authors' PLC_uncertain_discard (loss, running mean, low-loss indices) in 4 settings")


def run(args, cwd):
    out = subprocess.run(PY + args, cwd=cwd, capture_output=True, text=True, env=ENV)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]
    return out


def test_end_to_end():
    root = tempfile.mkdtemp(prefix="dcf_test_")
    make_dataset(os.path.join(root, "data/tiny"), 3, n_users=60)
    common = ["--data", "data/tiny", "--model", "lightgcn", "--lr", "0.01", "--reg", "0.0001", "--epochs", "6",
              "--patience", "10", "--seed", "1", "--device", "cpu"]
    run(["rq1kit.dcf", "--drop_rate", "0", "--relabel_ratio", "0", *common, "--run_dir", "runs/dcf0", "--no_export"], root)
    run(["rq1kit.backbone", "--loss", "bce", *common, "--run_dir", "runs/plain", "--no_export"], root)
    h1 = [json.loads(x)["valid_clean_ndcg@20"] for x in open(f"{root}/runs/dcf0/history.jsonl")]
    h2 = [json.loads(x)["valid_clean_ndcg@20"] for x in open(f"{root}/runs/plain/history.jsonl")]
    assert len(h1) == len(h2) == 6 and np.allclose(h1, h2, atol=1e-6), (h1, h2)
    print("ok  DCF(drop 0, relabel 0) trains exactly like Plain-BCE:", [round(x, 4) for x in h1])
    run(["rq1kit.dcf", "--relabel_ratio", "0.09", "--co_lambda", "0.01", "--time_step", "2", "--num_gradual", "20",
         *common, "--train_file", "train_N2_20_s1.tsv", "--run_dir", "runs/dcf"], root)
    run(["rq1kit.evaluate", "--data", "data/tiny", "--train_file", "train_N2_20_s1.tsv", "--topk", "runs/dcf/topk_test.npy",
         "--out", "results/dcf.json", "--tag", "method=DCF"], root)
    r = json.load(open(f"{root}/results/dcf.json"))
    rj = json.load(open(f"{root}/runs/dcf/run.json"))
    assert r["seen_item_leak_rate"] == 0 and rj["relabel_ratio"] == 0.09 and rj["loss"] == "bce"
    print(f"ok  DCF end to end on injected noise: test NDCG@20 {r['ndcg@20']:.4f}, leak 0, run.json complete")


if __name__ == "__main__":
    test_selftest()
    test_against_authors(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/repos/DCF"))
    test_end_to_end()
    print("ALL DCF TESTS PASSED")
