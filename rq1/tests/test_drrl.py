"""Tests for the DrRL adapter (rq1kit/drrl.py). CPU, about a minute.

  cd ~/rq1-kit && python tests/test_drrl.py [path to the authors' DrRL repository]

1. The loss and the margin update equal the authors' DrRLOptimizer.cal_loss on the same tensors (loaded from their
   repository with its cuda device call redirected to the CPU); skipped with a notice if the repository is absent.
2. Negatives are uniform over the items a user has not interacted with: never a training item.
3. End to end on a tiny dataset: runs, exports top-K lists with no seen-item leak, learning rate = --lr x --lr_mult,
   two runs with the same seed give identical validation scores (losses equal to 1e-5), and the method's grid has the keys the adapter accepts.
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import torch

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT)
sys.path.insert(0, os.path.join(KIT, "tests"))
from rq1kit.drrl import RenyiMargin, sample_negatives_many, softmax_loss  # noqa: E402
from test_partc import make_dataset  # noqa: E402

PY = [sys.executable, "-m"]
ENV = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONPATH": KIT}
AUTHORS = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/repos/DrRL")
if not os.path.isdir(AUTHORS):
    AUTHORS = "/home/claude/ext/drrl"


def test_loss_matches_authors():
    if not os.path.isfile(os.path.join(AUTHORS, "optimizer", "optim_DrRL.py")):
        print("skip  authors' repository not found, loss comparison not run")
        return
    sys.path.insert(0, AUTHORS)
    from optimizer.optim_DrRL import DrRLOptimizer
    real_full = torch.full

    def cpu_full(*a, **k):  # their __init__ allocates the margins on cuda
        k["device"] = "cpu"
        return real_full(*a, **k)

    class Fake(torch.nn.Module):
        def __init__(self, n):
            super().__init__()
            self.num_users = n
            self.w = torch.nn.Parameter(torch.zeros(1))
    nu, B, K = 50, 64, 32
    for omega, beta0, lr2 in ((1.2, 0.85, 1e-4), (1.1, 0.8, 1e-2), (1.27, 0.7, 1e-1)):
        cfg = {"lr": 1e-3, "weight_decay": 0, "lr2": lr2, "renyi_margin": beta0, "renyi_omega": omega,
               "num_negative_items": K, "neg_coefficient": 1}
        torch.full = cpu_full
        try:
            theirs = DrRLOptimizer(Fake(nu), cfg)
        finally:
                mine = RenyiMargin(nu, beta0, lr2, omega, K, 1.0, torch.device("cpu"))
        g = torch.Generator().manual_seed(1)
        for step in range(3):
            users = torch.randint(0, nu, (B,), generator=g)
            y = torch.rand(B, 1 + K, generator=g) * 2 - 1
            l_theirs = theirs.cal_loss(y_pred=y.clone(), margin_vec=theirs.margin_vector[users])
            l_mine = mine.loss(users, y.clone())
            assert torch.allclose(l_theirs, l_mine, atol=1e-6), (omega, step, l_theirs.item(), l_mine.item())
            assert torch.allclose(theirs.margin_vector.detach(), mine.margin.detach(), atol=1e-7), (omega, step)
    print("ok  loss and margin updates identical to the authors' DrRLOptimizer (3 settings x 3 steps)")
    from optimizer.optim_Softmax import SoftmaxOptimizer
    for temp in (0.08, 0.2, 0.25):
        sl = SoftmaxOptimizer(Fake(nu), {"lr": 1e-3, "weight_decay": 0, "ssm_temp": temp})
        y = torch.rand(B, 1 + K, generator=torch.Generator().manual_seed(2)) * 2 - 1
        assert torch.allclose(sl.cal_loss(y), softmax_loss(y, temp), atol=1e-6), temp
    print("ok  softmax loss (Plain-SL) identical to the authors' SoftmaxOptimizer at tau 0.08, 0.2, 0.25")


def test_negatives():
    nu, ni, n_neg = 20, 300, 50
    rng = np.random.default_rng(0)
    pairs = {(u, int(i)) for u in range(nu) for i in rng.choice(ni, 40, replace=False)}
    keys = torch.tensor(sorted(u * ni + i for u, i in pairs))
    users = torch.arange(nu).repeat_interleave(100)
    neg = sample_negatives_many(users, n_neg, ni, keys, torch.Generator().manual_seed(0))
    assert neg.shape == (nu * 100, n_neg)
    assert not any((int(u), int(i)) in pairs for u, row in zip(users.tolist(), neg.tolist()) for i in row), "a negative is a training item"
    counts = torch.bincount(neg[users == 0].flatten(), minlength=ni).float()
    allowed = torch.tensor([i for i in range(ni) if (0, i) not in pairs])
    share = counts[allowed] / counts.sum()
    assert float((share - 1 / len(allowed)).abs().max()) < 0.01 and counts.sum() == 100 * n_neg
    print("ok  negatives: never a training item, uniform over the other items (max deviation %.4f)" % float((share - 1 / len(allowed)).abs().max()))


def run(args, cwd):
    out = subprocess.run(PY + args, cwd=cwd, capture_output=True, text=True, env=ENV)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]


def test_end_to_end():
    root = tempfile.mkdtemp(prefix="drrl_test_")
    make_dataset(os.path.join(root, "data/tiny"), 4, n_users=60)
    common = ["--data", "data/tiny", "--model", "lightgcn", "--lr", "0.005", "--lr_mult", "10", "--reg", "0.0001",
              "--epochs", "4", "--patience", "10", "--seed", "1", "--device", "cpu", "--num_negative_items", "16",
              "--renyi_omega", "1.2", "--renyi_margin", "0.85", "--lr2", "0.0001"]
    run(["rq1kit.drrl", *common, "--run_dir", "runs/a"], root)
    run(["rq1kit.drrl", *common, "--run_dir", "runs/b", "--no_export"], root)
    info = json.load(open(f"{root}/runs/a/run.json"))
    assert abs(info["lr_effective"] - 0.05) < 1e-12 and info["loss"] == "drrl", info
    ha = [json.loads(x) for x in open(f"{root}/runs/a/history.jsonl")]
    hb = [json.loads(x) for x in open(f"{root}/runs/b/history.jsonl")]
    assert len(ha) == 4 and all(x["valid_clean_ndcg@20"] == y["valid_clean_ndcg@20"] and abs(x["loss"] - y["loss"]) < 1e-5 for x, y in zip(ha, hb))
    run(["rq1kit.evaluate", "--data", "data/tiny", "--train_file", "train.tsv", "--topk", "runs/a/topk_test.npy",
         "--out", "results/drrl.json", "--tag", "method=DrRL"], root)
    r = json.load(open(f"{root}/results/drrl.json"))
    assert r["seen_item_leak_rate"] == 0
    run(["rq1kit.drrl", *common[:-6], "--model", "mf", "--run_dir", "runs/mf", "--no_export"], root)
    run(["rq1kit.drrl", *common[:-6], "--loss", "sl", "--ssm_temp", "0.2", "--run_dir", "runs/sl", "--no_export"], root)
    assert json.load(open(f"{root}/runs/sl/run.json"))["loss"] == "sl"
    grid = json.load(open(os.path.join(KIT, "configs/partc/methods/drrl.json")))["grid"]
    assert len(grid) == 8 and all(set(g) == {"lr_mult", "renyi_omega", "renyi_margin"} for g in grid)
    grid = json.load(open(os.path.join(KIT, "configs/partc/methods/sl.json")))["grid"]
    assert len(grid) == 8 and all(set(g) == {"lr_mult", "ssm_temp"} for g in grid)
    print(f"ok  end to end: lr 0.005 x 10 = 0.05, reruns identical, test NDCG@20 {r['ndcg@20']:.4f}, no leak, MF and SL runs, grid keys valid")


if __name__ == "__main__":
    test_loss_matches_authors()
    test_negatives()
    test_end_to_end()
    print("ALL DRRL TESTS PASSED")
