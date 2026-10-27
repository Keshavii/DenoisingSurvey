"""Tests for the PLD adapter (rq1kit/pld.py). CPU, about a minute.

  cd ~/rq1-kit && python tests/test_pld.py

1. Candidate pools: always the user's own training items; k distinct items when the user has at least k (uniform
   over k-subsets), draws with replacement otherwise.
2. The vectorised pre-selection gives exactly the authors' choice (their repeat_interleave / view / softmax /
   multinomial lines from utls/trainer.py) under the same random seed.
3. With resampling switched off (--begin_adv beyond the last epoch) PLD trains exactly like Plain-BPR; a normal
   PLD run exports top-K lists with no seen-item leak.
"""
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter

import numpy as np
import scipy.sparse as sp
import torch
import torch.nn.functional as F

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT)
sys.path.insert(0, os.path.join(KIT, "tests"))
from rq1kit.pld import pld_select, sample_candidates  # noqa: E402
from test_partc import make_dataset  # noqa: E402

PY = [sys.executable, "-m"]
ENV = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONPATH": KIT}


def test_candidates():
    rng = np.random.default_rng(0)
    rows = [np.arange(3), np.arange(10, 15), np.arange(20, 40)]  # degrees 3, 5, 20
    m = sp.csr_matrix((np.ones(28), (np.repeat([0, 1, 2], [3, 5, 20]), np.concatenate(rows))), shape=(3, 50))
    ip, ix = m.indptr.astype(np.int64), m.indices.astype(np.int64)
    users = np.repeat([0, 1, 2], 4000)
    c = sample_candidates(users, 5, ip, ix, rng)
    for r, items in enumerate(rows):
        cr = c[users == r]
        assert np.isin(cr, items).all(), "candidate outside the user's training items"
    assert all(len(set(x)) == 5 for x in c[users == 1]) and all(len(set(x)) == 5 for x in c[users == 2])
    assert any(len(set(x)) < 5 for x in c[users == 0]), "users with fewer than k items should be drawn with replacement"
    freq = Counter(c[users == 2].ravel())
    share = np.array([freq[i] for i in rows[2]]) / (4000 * 5)
    assert np.abs(share - 1 / 20).max() < 0.01, share
    print("ok  candidate pools: own items, distinct when possible, uniform (max deviation %.4f)" % np.abs(share - 0.05).max())


def test_selection_matches_authors():
    g = torch.Generator().manual_seed(0)
    B, k, d, ni = 300, 5, 16, 400
    Ud, Id = torch.randn(B, d, generator=g), torch.randn(ni, d, generator=g)
    u = torch.arange(B)
    cand = torch.randint(0, ni, (B, k), generator=g)
    n = torch.randint(0, ni, (B,), generator=g)
    for temp in (0.01, 0.1, 0.5):
        torch.manual_seed(7)
        mine = pld_select(Ud, Id, u, cand, n, temp)
        # the authors' lines (utls/trainer.py, PLDCFTrainer._train_epoch), MF scores
        torch.manual_seed(7)
        pos_flat = cand.flatten()
        u_rep = u.repeat_interleave(k)
        n_rep = n.repeat_interleave(k)
        pos_logits = torch.sum(Ud[u_rep] * Id[pos_flat], dim=1)
        neg_logits = torch.sum(Ud[u_rep] * Id[n_rep], dim=1)
        temp_loss = F.softplus(neg_logits - pos_logits).detach().view(B, k)
        probs = torch.nn.functional.softmax(-temp_loss / temp, dim=1)
        idx = torch.multinomial(probs, 1, replacement=False).squeeze()
        theirs = torch.gather(cand, 1, idx.unsqueeze(-1)).squeeze()
        assert torch.equal(mine, theirs), (temp, (mine != theirs).sum())
    print("ok  pre-selection identical to the authors' code at temperatures 0.01, 0.1, 0.5")


def run(args, cwd):
    out = subprocess.run(PY + args, cwd=cwd, capture_output=True, text=True, env=ENV)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]


def test_end_to_end():
    root = tempfile.mkdtemp(prefix="pld_test_")
    make_dataset(os.path.join(root, "data/tiny"), 4, n_users=60)
    common = ["--data", "data/tiny", "--model", "lightgcn", "--lr", "0.01", "--reg", "0.0001", "--epochs", "6",
              "--patience", "10", "--seed", "1", "--device", "cpu"]
    run(["rq1kit.pld", "--begin_adv", "1000", *common, "--run_dir", "runs/off", "--no_export"], root)
    run(["rq1kit.backbone", "--loss", "bpr", *common, "--run_dir", "runs/plain", "--no_export"], root)
    h1 = [json.loads(x)["valid_clean_ndcg@20"] for x in open(f"{root}/runs/off/history.jsonl")]
    h2 = [json.loads(x)["valid_clean_ndcg@20"] for x in open(f"{root}/runs/plain/history.jsonl")]
    assert len(h1) == 6 and np.allclose(h1, h2, atol=1e-6), (h1, h2)
    print("ok  PLD with resampling off trains exactly like Plain-BPR:", [round(x, 4) for x in h1])
    run(["rq1kit.pld", "--begin_adv", "1", "--item_num", "5", "--temp", "0.05", *common, "--train_file", "train_N2_20_s1.tsv",
         "--run_dir", "runs/pld"], root)
    run(["rq1kit.evaluate", "--data", "data/tiny", "--train_file", "train_N2_20_s1.tsv", "--topk", "runs/pld/topk_test.npy",
         "--out", "results/pld.json", "--tag", "method=PLD"], root)
    r = json.load(open(f"{root}/results/pld.json"))
    h = [json.loads(x) for x in open(f"{root}/runs/pld/history.jsonl")]
    assert r["seen_item_leak_rate"] == 0 and h[0]["resample"] is False and h[1]["resample"] is True
    print(f"ok  PLD end to end on injected noise: test NDCG@20 {r['ndcg@20']:.4f}, leak 0, resampling from epoch 2")


if __name__ == "__main__":
    test_candidates()
    test_selection_matches_authors()
    test_end_to_end()
    print("ALL PLD TESTS PASSED")
