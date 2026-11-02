"""Experiment 2 (Experiment Design PDF): does the best method stay best when the test-time noise level shifts?

Models are trained with injected noise at rho_val (the kit's N2_<rho> training files). Each saved top-K list is then
scored against test sets that contain extra fake positives at rho_test. The fakes are drawn once per
(dataset, kind, rho_test, seed) and shared by every method, so differences between methods come from the methods only.
Training code of every method is untouched: this works on the exported topk_test.npy files.

  fake test item for user u = an item that u has never interacted with in train, validation or test
  kind "N1" uniform over those items, "N2" proportional to training degree (matches the N2 training noise)
  count per user = stochastic rounding of rho_test x (number of clean test items of that user)

Usage:
  python -m rq1kit.e2 --data data/ml1m --rho_val 20 --methods plain_bpr,tce,rce,bod,pld \
      --run_glob 'runs/ml1m/{method}_lightgcn_N2_{rho}_s{seed}/topk_test.npy' --out results/E2/ml1m_rv20.json
"""
import argparse
import json
import os

import numpy as np
import pandas as pd
import scipy.sparse as sp

from .data import load_split, to_csr
from .evaluate import _per_user_metrics


def rho_tests(rho_val):
    """The PDF's four test-time conditions: rho_val - 10, rho_val, rho_val + 10, rho_val + 20 (percent)."""
    return [r for r in (rho_val - 10, rho_val, rho_val + 10, rho_val + 20) if r >= 0]


def noisy_test(data_dir, rho_test, kind="N2", seed=1, train_file="train.tsv"):
    """Test truth with fake positives added. rho_test in percent. Returns (csr, n_fake)."""
    meta, train, valid_clean, valid_noisy, test = load_split(data_dir, train_file)
    nu, ni = meta["n_users"], meta["n_items"]
    clean = to_csr(test, nu, ni)
    if rho_test == 0:
        return clean, 0
    seen = to_csr(pd.concat([train[["user", "item"]], valid_noisy[["user", "item"]], test[["user", "item"]]]), nu, ni)
    deg = np.asarray(to_csr(train[["user", "item"]], nu, ni).sum(0)).ravel().astype(float)
    base = np.ones(ni) if kind == "N1" else deg
    rng = np.random.default_rng([seed, int(rho_test), 1 if kind == "N1" else 2])
    rows, cols = [], []
    for u in range(nu):
        n_clean = clean.indptr[u + 1] - clean.indptr[u]
        if n_clean == 0:
            continue
        x = n_clean * rho_test / 100.0
        n = int(np.floor(x)) + int(rng.random() < x - np.floor(x))
        if n == 0:
            continue
        w = base.copy()
        w[seen.indices[seen.indptr[u]:seen.indptr[u + 1]]] = 0
        if w.sum() <= 0 or (w > 0).sum() < n:
            continue
        pick = rng.choice(ni, size=n, replace=False, p=w / w.sum())
        rows += [u] * n
        cols += pick.tolist()
    fake = sp.csr_matrix((np.ones(len(rows), dtype=np.int8), (rows, cols)), shape=(nu, ni))
    return (clean + fake).tocsr(), len(rows)


def score(topk_path, truth_csr):
    users, m = _per_user_metrics(np.load(topk_path), truth_csr, ks=(20,))
    return float(m["ndcg@20"].mean()), float(m["recall@20"].mean())


def kendall(a, b):
    from scipy.stats import kendalltau
    t = kendalltau(a, b)[0]
    return None if t != t else float(t)


def run(data_dir, methods, rho_val, run_glob, seeds=(1, 2, 3), kinds=("N1", "N2"), train_tmpl="train_N2_{rho}_s{seed}.tsv"):
    """Returns nested result {kind: {rho_test: {method: mean ndcg@20}}} plus Kendall tau against rho_test == rho_val."""
    out = {"rho_val": rho_val, "kinds": {}}
    for kind in kinds:
        table = {}
        for rt in rho_tests(rho_val):
            per_method = {}
            for m in methods:
                vals = []
                for s in seeds:
                    path = run_glob.format(method=m, rho=rho_val, seed=s)
                    if not os.path.exists(path):
                        continue
                    truth, _ = noisy_test(data_dir, rt, kind, seed=s, train_file=train_tmpl.format(rho=rho_val, seed=s))
                    vals.append(score(path, truth)[0])
                if vals:
                    per_method[m] = dict(ndcg20=float(np.mean(vals)), n_seeds=len(vals))
            table[rt] = per_method
        ref = table[rho_val]
        taus = {}
        for rt, pm in table.items():
            common = [m for m in ref if m in pm]
            if len(common) >= 3:
                taus[rt] = kendall([ref[m]["ndcg20"] for m in common], [pm[m]["ndcg20"] for m in common])
        ranks = {rt: sorted(pm, key=lambda m: -pm[m]["ndcg20"]) for rt, pm in table.items()}
        out["kinds"][kind] = dict(ndcg20=table, kendall_tau_vs_rho_val=taus, ranking=ranks)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--rho_val", type=int, required=True, choices=[10, 20])
    ap.add_argument("--methods", required=True)
    ap.add_argument("--run_glob", required=True, help="path template with {method} {rho} {seed}")
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--kinds", default="N1,N2")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = run(a.data, a.methods.split(","), a.rho_val, a.run_glob, [int(s) for s in a.seeds.split(",")], a.kinds.split(","))
    res["data"] = a.data
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=2)
    for k, v in res["kinds"].items():
        print(k, "tau vs rho_val:", v["kendall_tau_vs_rho_val"])
        for rt, r in v["ranking"].items():
            print("  rho_test", rt, "->", " > ".join(r))


if __name__ == "__main__":
    main()
