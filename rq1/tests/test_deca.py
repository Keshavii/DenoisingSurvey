"""Tests for the DeCA adapter (rq1kit/deca.py). CPU, about a minute.

  cd ~/rq1-kit && python tests/test_deca.py [path to the authors' DeCA repository]

1. The adapter's loss equals the authors' (train.py TrainModel.positive_loss_function, negative_loss_function,
   KL_loss, KL, combined as in RS_train), in each mode (both, DP, DN) and at several (C1, C2, alpha), with the authors'
   own MF models; values and gradients w.r.t. the recommender's, the auxiliary and the hypothesis models' parameters.
   The mode sequence is both, DP, DN, DP, ... Skipped with a notice if the repository is absent.
2. End to end on a tiny dataset: trains, exports top-K lists with no seen-item leak, identical reruns, grid keys valid.
"""
import importlib
import json
import os
import subprocess
import sys
import tempfile

import torch

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT)
sys.path.insert(0, os.path.join(KIT, "tests"))
from rq1kit.deca import ProbMF, deca_loss, next_kind  # noqa: E402
from test_partc import make_dataset  # noqa: E402

PY = [sys.executable, "-m"]
ENV = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONPATH": KIT}
AUTHORS = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/repos/DeCA")
if not os.path.isdir(AUTHORS):
    AUTHORS = "/home/claude/ext/DeCA"


def test_matches_authors():
    if not os.path.isfile(os.path.join(AUTHORS, "train.py")):
        print("skip  authors' repository not found, comparison not run")
        return
    sys.path.insert(0, AUTHORS)
    T = importlib.import_module("train")
    M = importlib.import_module("model")
    nu, ni, B = 30, 40, 24
    g = torch.Generator().manual_seed(2)
    u = torch.randint(0, nu, (B,), generator=g)
    p = torch.randint(0, ni, (B,), generator=g)
    n = torch.randint(0, ni, (B,), generator=g)
    for kind in ("both", "DP", "DN"):
        for c1, c2, alpha in ((10.0, 1000.0, 0.0), (1000.0, 10.0, 1.0), (100.0, 100.0, 0.5)):
            torch.manual_seed(7)
            f, a_, h1, h2 = (M.MF(nu, ni, 8) for _ in range(4))
            for m in (f, a_, h1, h2):  # larger than their 0.01 init so the terms are not all ~0
                torch.nn.init.normal_(m.user_embedding.weight, std=0.5)
                torch.nn.init.normal_(m.item_embedding.weight, std=0.5)
            tm = T.TrainModel.__new__(T.TrainModel)
            tm.method, tm.alpha, tm.C_1, tm.C_2, tm.denoise_type = "DeCA", alpha, c1, c2, kind
            tm.aux_model, tm.h_model_1, tm.h_model_2 = a_, h1, h2
            # authors' RS_train, variational branch, one batch
            tp, tn = f(u, p), f(u, n)
            theirs = torch.mean(tm.KL_loss(u, p, tp) - tm.positive_loss_function(u, p, tp, 0)) + \
                torch.mean(tm.KL_loss(u, n, tn) - tm.negative_loss_function(u, n, tn, 0)) * 1
            nets = (f, a_, h1, h2)
            gt = torch.autograd.grad(theirs, [q for m in nets for q in m.parameters()], allow_unused=True)
            # the adapter, same weights
            mine_nets = [ProbMF(nu, ni, 8) for _ in range(4)]
            for mm, m in zip(mine_nets, nets):
                mm.load_state_dict(m.state_dict())
            mf, ma, mh1, mh2 = mine_nets
            mine = deca_loss(kind, mf(u, p), mf(u, n), ma(u, p), ma(u, n), mh1(u, p), mh1(u, n), mh2(u, p), mh2(u, n),
                             c1, c2, alpha)
            gm = torch.autograd.grad(mine, [q for m in mine_nets for q in m.parameters()], allow_unused=True)
            assert torch.allclose(theirs, mine, rtol=1e-5, atol=1e-7), (kind, c1, c2, alpha, theirs.item(), mine.item())
            for x, y in zip(gm, gt):
                if y is None:
                    assert x is None or x.abs().max() == 0
                else:
                    assert x is not None and (x - y).abs().max().item() <= 1e-5 * y.abs().max().item() + 1e-9
    seq, k = [], "both"
    for _ in range(5):
        seq.append(k)
        k = next_kind(k)
    assert seq == ["both", "DP", "DN", "DP", "DN"], seq
    print("ok  loss and gradients identical to the authors' DeCA in modes both / DP / DN at three (C1, C2, alpha); mode sequence both, DP, DN, DP, DN")


def run(args, cwd):
    out = subprocess.run(PY + args, cwd=cwd, capture_output=True, text=True, env=ENV)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]


def test_end_to_end():
    root = tempfile.mkdtemp(prefix="deca_test_")
    make_dataset(os.path.join(root, "data/tiny"), 4, n_users=60)
    for model in ("lightgcn", "mf"):
        common = ["--data", "data/tiny", "--model", model, "--lr", "0.005", "--epochs", "4", "--patience", "10",
                  "--seed", "1", "--device", "cpu", "--batch", "64", "--dim", "16", "--layers", "2"]
        run(["rq1kit.deca", *common, "--train_file", "train_N2_20_s1.tsv", "--run_dir", f"runs/{model}_a"], root)
        run(["rq1kit.deca", *common, "--train_file", "train_N2_20_s1.tsv", "--run_dir", f"runs/{model}_b", "--no_export"], root)
        ha = [json.loads(x) for x in open(f"{root}/runs/{model}_a/history.jsonl")]
        hb = [json.loads(x) for x in open(f"{root}/runs/{model}_b/history.jsonl")]
        assert len(ha) == 4 and all(x["valid_clean_ndcg@20"] == y["valid_clean_ndcg@20"] for x, y in zip(ha, hb)), (ha, hb)
    run(["rq1kit.evaluate", "--data", "data/tiny", "--train_file", "train_N2_20_s1.tsv", "--topk", "runs/lightgcn_a/topk_test.npy",
         "--out", "results/deca.json", "--tag", "method=DeCA"], root)
    r = json.load(open(f"{root}/results/deca.json"))
    assert r["seen_item_leak_rate"] == 0
    grid = json.load(open(os.path.join(KIT, "configs/partc/methods/deca.json")))["grid"]
    assert len(grid) == 8 and all(set(x) == {"C_1", "C_2", "alpha"} for x in grid)
    print(f"ok  end to end on LightGCN and MF: reruns identical, test NDCG@20 {r['ndcg@20']:.4f}, no leak, grid keys valid")


if __name__ == "__main__":
    test_matches_authors()
    test_end_to_end()
    print("ALL DECA TESTS PASSED")
