"""Tests for RQ4 (rq1kit/rq4.py, rq1kit/rq4_llm.py, scripts/rq4_jobs.py). CPU, a few minutes.

1. Signal L1 with Drop reproduces rq1kit.adt T-CE exactly, and no treatment reproduces Plain-BCE (R-CE alpha 0).
2. Treatments: rank helpers, reweight/relabel with no effect equal plain BCE, drop removes the most suspicious.
3. ROC-AUC matches a direct pairwise count.
4. Every signal x treatment trains end to end on a tiny dataset (R2 trains its reference model, R4 reads LLM
   item embeddings, R5 reads Llama scores written by rq4_llm with a stub judge), logs a detection AUC, exports
   top-K lists with no seen-item leak.
5. Job lists: counts, grid keys never collide with the backbone's --lr / --reg, picks.
"""
import json
import os
import pickle
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd
import torch

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT)
sys.path.insert(0, os.path.join(KIT, "tests"))
from rq1kit import rq4, rq4_llm  # noqa: E402
from test_partc import make_dataset  # noqa: E402

PY = [sys.executable, "-m"]
ENV = dict(os.environ, PYTHONPATH=KIT, OMP_NUM_THREADS="2")


def run(args, cwd):
    out = subprocess.run(PY + args, cwd=cwd, capture_output=True, text=True, env=ENV)
    assert out.returncode == 0, " ".join(args) + "\n" + out.stdout[-3000:] + out.stderr[-3000:]
    return out.stdout


def hist(path):
    return [json.loads(x) for x in open(path)]


def test_equivalence(root):
    common = ["--data", "data/tiny", "--lr", "0.01", "--reg", "1e-4", "--epochs", "6", "--patience", "50", "--seed", "3",
              "--device", "cpu", "--batch", "64", "--dim", "16", "--layers", "2", "--no_export"]
    run(["rq1kit.adt", "--method", "tce", "--drop_rate", "0.2", "--num_gradual", "20", "--run_dir", "runs/tce", *common], root)
    run(["rq1kit.rq4", "--signal", "L1", "--treat", "drop", "--rate", "0.2", "--num_gradual", "20", "--run_dir", "runs/l1drop",
         *common], root)
    a, b = hist(f"{root}/runs/tce/history.jsonl"), hist(f"{root}/runs/l1drop/history.jsonl")
    assert [x["valid_clean_ndcg@20"] for x in a] == [x["valid_clean_ndcg@20"] for x in b], (a, b)
    assert [x["loss"] for x in a] == [x["loss"] for x in b]
    run(["rq1kit.adt", "--method", "rce", "--alpha", "0", "--run_dir", "runs/rce0", *common], root)
    run(["rq1kit.rq4", "--signal", "none", "--treat", "none", "--run_dir", "runs/plain", *common], root)
    a, b = hist(f"{root}/runs/rce0/history.jsonl"), hist(f"{root}/runs/plain/history.jsonl")
    assert np.allclose([x["valid_clean_ndcg@20"] for x in a], [x["valid_clean_ndcg@20"] for x in b], atol=1e-6)
    print("ok  L1 + Drop = T-CE (identical history); no treatment = Plain-BCE")


def test_treatments():
    s = torch.tensor([0.3, float("nan"), 0.1, 0.9])
    q = rq4.batch_rank(s)
    assert torch.isnan(q[1]) and q[2] == 0 and q[3] == 1 and abs(float(q[0]) - 0.5) < 1e-6
    r = rq4.row_rank(torch.tensor([[3.0, 1.0, float("nan")], [0.0, 2.0, 1.0]]))
    assert r.tolist() == [[0.5, 0.0, 0.5], [0.0, 1.0, 0.5]], r
    g = torch.Generator().manual_seed(0)
    pos, neg, susp = torch.randn(200, generator=g), torch.randn(200, generator=g), torch.rand(200, generator=g)
    plain = rq4.treated_loss("none", pos, neg, None, 0, 0)
    assert torch.allclose(plain, rq4.treated_loss("reweight", pos, neg, susp, 0, 0.0), atol=1e-6)
    assert torch.allclose(plain, rq4.treated_loss("relabel", pos, neg, susp, 0.0, 0), atol=1e-6)
    assert torch.allclose(plain, rq4.treated_loss("drop", pos, neg, susp, 0.0, 0), atol=1e-6)
    # drop 10% of the 400 samples = the 40 most suspicious positives
    keep = torch.argsort(susp)[:160]
    manual = 2 * torch.nn.functional.binary_cross_entropy_with_logits(
        torch.cat([pos[keep], neg]), torch.cat([torch.ones(160), torch.zeros(200)]))
    assert torch.allclose(manual, rq4.treated_loss("drop", pos, neg, susp, 0.1, 0), atol=1e-6)
    # unscored positives are never dropped before scored ones
    s2 = susp.clone(); s2[:50] = float("nan")
    l2 = rq4.treated_loss("drop", pos, neg, s2, 0.1, 0)
    keep2 = torch.cat([torch.arange(50), 50 + torch.argsort(susp[50:])[:110]])
    m2 = 2 * torch.nn.functional.binary_cross_entropy_with_logits(
        torch.cat([pos[keep2], neg]), torch.cat([torch.ones(160), torch.zeros(200)]))
    assert torch.allclose(l2, m2, atol=1e-6)
    print("ok  treatments: ranks, no-effect settings = plain BCE, drop removes the most suspicious, unscored kept")


def test_auc():
    rng = np.random.default_rng(0)
    s, y = rng.random(300), rng.random(300) < 0.3
    s[:20] = 0.5  # ties
    pairs = (s[y][:, None] > s[~y][None, :]).mean() + 0.5 * (s[y][:, None] == s[~y][None, :]).mean()
    assert abs(rq4.roc_auc(s, y) - pairs) < 1e-9
    assert rq4.roc_auc(s, np.zeros(300, bool)) is None
    print("ok  ROC-AUC matches the pairwise count, ties half")


def fake_inputs(root, ni):
    # R4: LLM item-profile embeddings; R5 needs raw MovieLens-style text files for rq4_llm
    d = f"{root}/data/tiny/llard/N0/prf_k"
    os.makedirs(d)
    pickle.dump(np.random.default_rng(1).standard_normal((ni, 8)).astype(np.float32), open(f"{d}/itm_emb_np.pkl", "wb"))
    raw = f"{root}/raw"
    os.makedirs(raw)
    pd.DataFrame({"user_id:token": [1] * ni, "item_id:token": np.arange(100, 100 + ni), "rating:float": 4}).to_csv(
        f"{raw}/ml-1m.inter", sep="\t", index=False)
    genres = ["Drama", "Comedy", "Action", "Horror"]
    pd.DataFrame({"item_id:token": np.arange(100, 100 + ni), "movie_title:token_seq": [f"Movie {k}" for k in range(ni)],
                  "release_year:token": 1990, "genre:token_seq": [genres[k % 4] for k in range(ni)]}).to_csv(
        f"{raw}/ml-1m.item", sep="\t", index=False)
    return raw


def test_end_to_end(root):
    meta = json.load(open(f"{root}/data/tiny/meta.json"))
    raw = fake_inputs(root, meta["n_items"])
    tf = "train_N2_20_s1.tsv"
    common = ["--data", "data/tiny", "--train_file", tf, "--lr", "0.01", "--reg", "1e-4", "--seed", "1", "--device", "cpu",
              "--batch", "64", "--dim", "16", "--layers", "2", "--patience", "50", "--ref_epochs", "5"]
    ref = run(["rq1kit.rq4", "--make_ref", "--run_dir", "runs/unused", *common], root).strip().splitlines()[-1]
    assert os.path.isfile(os.path.join(root, ref, "emb.npz"))
    rq4_llm.main(["--data", f"{root}/data/tiny", "--train_file", tf, "--ref", os.path.join(root, ref), "--raw", raw,
                  "--backend", "stub", "--chunk", "7"])
    z = np.load(f"{root}/data/tiny/rq4_llm/N2_20_s1.npz")
    n_train = len(pd.read_csv(f"{root}/data/tiny/{tf}", sep="\t").drop_duplicates(["user", "item"]))
    assert len(z["user"]) == int(round(0.2 * n_train)) and np.isfinite(z["p_noise"]).all()
    assert np.all(np.isclose(z["p_noise"], 0.2, atol=1e-6) | np.isclose(z["p_noise"], 0.9, atol=1e-6))
    for signal in rq4.SIGNALS[1:]:
        for treat in rq4.TREATS[1:]:
            rd = f"runs/e2e/{signal}_{treat}"
            run(["rq1kit.rq4", "--signal", signal, "--treat", treat, "--epochs", "7", "--begin_resample", "1",
                 "--num_gradual", "10", "--run_dir", rd, *common, *(["--no_export"] if treat != "drop" else [])], root)
            info = json.load(open(f"{root}/{rd}/run.json"))
            assert info["epochs_run"] == 7 and info["n_noisy_train"] > 0
            aucs = [h["detection_auc"] for h in hist(f"{root}/{rd}/history.jsonl") if h.get("detection_auc") is not None]
            assert aucs and all(0 <= x <= 1 for x in aucs), (signal, treat, aucs)
        out = f"results/{signal}.json"
        run(["rq1kit.evaluate", "--data", "data/tiny", "--train_file", tf, "--topk", f"runs/e2e/{signal}_drop/topk_test.npy",
             "--out", out, "--tag", f"signal={signal}"], root)
        assert json.load(open(f"{root}/{out}"))["seen_item_leak_rate"] == 0
    # identical reruns
    run(["rq1kit.rq4", "--signal", "P2", "--treat", "resample", "--epochs", "4", "--begin_resample", "1", "--run_dir", "runs/r1",
         "--no_export", *common], root)
    run(["rq1kit.rq4", "--signal", "P2", "--treat", "resample", "--epochs", "4", "--begin_resample", "1", "--run_dir", "runs/r2",
         "--no_export", *common], root)
    assert hist(f"{root}/runs/r1/history.jsonl")[-1]["valid_clean_ndcg@20"] == hist(f"{root}/runs/r2/history.jsonl")[-1]["valid_clean_ndcg@20"]
    print(f"ok  all {len(rq4.SIGNALS) - 1} signals x {len(rq4.TREATS) - 1} treatments train, log detection AUC, export "
          "with no leak; reruns identical; reference model and LLM scores built")


def test_jobs(root):
    sys.path.insert(0, os.path.join(KIT, "scripts"))
    import rq4_jobs as J
    t = J.tune_jobs()
    assert len(t) == 3 * 4 * (11 + 9)
    for k, (key, _) in J.GRID.items():
        assert key not in ("lr", "reg", "seed", "data")
    assert all("--epochs 100 --seed 0 --no_export" in j["cmd"] for j in t)
    for j in t[:3]:  # tuned cells pass both backbone settings and one grid value
        assert j["cmd"].count("--lr ") == 1 and j["cmd"].count("--reg ") == 1
    fake = {f"{ds}|{s}|{x}": {J.GRID[x][0]: J.GRID[x][1][1]} for ds in J.DATASETS for s, x in J.cells(ds)}
    f = J.final_jobs(fake)
    assert len(f) == (44 + 1) * 3 * 3 + 3 + (36 + 1) * 2 * 2 + 2
    assert any("train_N3_20_s2.tsv" in j["cmd"] and "--signal R5" in j["cmd"] for j in f)
    assert not any("--signal R5" in j["cmd"] and "data/yelp" in j["cmd"] for j in f)
    # picks from tuning folders
    for k, v in enumerate([0.1, 0.3, 0.2]):
        d = f"{root}/{J.TUNE_DIR}/ml1m/L1_drop_t{k}"
        os.makedirs(d)
        json.dump({"best_valid_ndcg@20": v}, open(f"{d}/run.json", "w"))
    best, missing = J.pick(root)
    assert best["ml1m|L1|drop"]["rate"] == 0.1 and best["ml1m|L1|drop"]["complete"] and len(missing) == len(t) // 3 - 1
    print(f"ok  job lists: {len(t)} tuning trials, {len(f)} finals, picks from tuning folders")


if __name__ == "__main__":
    root = tempfile.mkdtemp(prefix="rq4_test_")
    make_dataset(os.path.join(root, "data/tiny"), 5, n_users=80, n_items=40, per_user=10)
    test_treatments()
    test_auc()
    test_equivalence(root)
    test_end_to_end(root)
    test_jobs(root)
    print("ALL RQ4 TESTS PASSED")
