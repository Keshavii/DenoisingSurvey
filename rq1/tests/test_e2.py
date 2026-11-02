"""Tests for rq1kit.e2: fakes are valid, shared across methods, reproducible, and scoring behaves as expected."""
import os, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_partc import make_dataset
from rq1kit import e2
from rq1kit.data import load_split, to_csr

tmp = tempfile.mkdtemp()
d = os.path.join(tmp, "data")
make_dataset(d, 0, n_users=200, n_items=60)
meta, train, vc, vn, test = load_split(d)
nu, ni = meta["n_users"], meta["n_items"]
clean = to_csr(test, nu, ni)

t0, n0 = e2.noisy_test(d, 0)
assert n0 == 0 and (t0 != clean).nnz == 0
for kind in ("N1", "N2"):
    for rt in (10, 30):
        a, na = e2.noisy_test(d, rt, kind, seed=1)
        b, nb = e2.noisy_test(d, rt, kind, seed=1)
        assert (a != b).nnz == 0 and na == nb, "must be reproducible"
        assert (a - clean).min() >= 0, "clean items must stay"
        fake = (a - clean).tocsr()
        seen = to_csr(__import__("pandas").concat([train[["user", "item"]], vn[["user", "item"]], test[["user", "item"]]]), nu, ni)
        assert seen.multiply(fake).nnz == 0, "fakes must be unobserved items"
        assert abs(na / clean.nnz - rt / 100) < 0.05, (na, clean.nnz, rt)
c, _ = e2.noisy_test(d, 30, "N2", seed=2)
assert (c != e2.noisy_test(d, 30, "N2", seed=1)[0]).nnz > 0, "seed must change the draw"

# scoring: a list that ranks the clean test item first beats a random list, more so at low noise
rng = np.random.default_rng(0)
good = np.full((nu, 50), -1)
rand = np.zeros((nu, 50), dtype=int)
for u in range(nu):
    ti = clean.indices[clean.indptr[u]:clean.indptr[u + 1]]
    rest = rng.permutation([i for i in range(ni) if i not in ti])[:49]
    good[u] = np.concatenate([ti, rest])[:50] if len(ti) else rest[:50]
    rand[u] = rng.permutation(ni)[:50]
gp, rp = os.path.join(tmp, "good.npy"), os.path.join(tmp, "rand.npy")
np.save(gp, good); np.save(rp, rand)
s_clean = e2.score(gp, clean)[0]
s_noisy = e2.score(gp, e2.noisy_test(d, 40, "N1")[0])[0]
assert s_clean > e2.score(rp, clean)[0] and s_noisy < s_clean

# end to end with three fake "methods" laid out as run_glob expects
for m, arr in (("a", good), ("b", rand), ("c", good[:, ::-1].copy())):
    for s in (1, 2):
        p = os.path.join(tmp, f"{m}_{s}.npy"); np.save(p, arr)
res = e2.run(d, ["a", "b", "c"], 20, os.path.join(tmp, "{method}_{seed}.npy"), seeds=(1, 2), kinds=("N1",),
             train_tmpl="train.tsv")
k = res["kinds"]["N1"]
assert set(k["ndcg20"]) == {10, 20, 30, 40}
assert k["ranking"][20][0] == "a" and abs(k["kendall_tau_vs_rho_val"][20] - 1.0) < 1e-9
assert k["ndcg20"][10]["a"]["ndcg20"] > k["ndcg20"][40]["a"]["ndcg20"], "more test noise lowers NDCG"

# training-noise shift variant: A,B,C,D -> B,A,D,C has 2 discordant pairs of 6, tau = 1/3
import json
from rq1kit import e2_shift
rd = os.path.join(tmp, "res"); os.makedirs(rd + "/ml1m")
for m, (x, y) in {"A": (.10, .07), "B": (.09, .08), "C": (.08, .05), "D": (.07, .06)}.items():
    for c, val in (("N0", x), ("N2_20", y)):
        for sd in (1, 2):
            json.dump(dict(dataset="ml1m", method=m, backbone="LightGCN", cond=c, seed=sd, **{"ndcg@20": val}),
                      open(f"{rd}/ml1m/{m}_{c}_{sd}.json", "w"))
tbl, sds = e2_shift.load(rd, "LightGCN")
r = e2_shift.shift(tbl)["ml1m"]
bt = e2_shift.bootstrap_tau(sds, "ml1m", n=200)
assert abs(bt[0] - 1 / 3) < 1e-9 and bt[1] == bt[2], bt  # identical seeds: no spread
assert r["best_a"] == "A" and r["best_b"] == "B" and abs(r["tau"] - 1 / 3) < 1e-9, r

# E7/E8 tidy table: % change vs Plain-BPR, seed averaging
from rq1kit import e78
r7 = os.path.join(tmp, "r7"); os.makedirs(r7 + "/ml1m")
for sd in (1, 2):
    for m, nd, cold, tail in (("Plain-BPR", .10, .04, .02), ("X", .12, .06, .01)):
        json.dump({"dataset": "ml1m", "method": m, "backbone": "LightGCN", "cond": "N2_20", "seed": sd, "ndcg@20": nd,
                   "recall@20": 2 * nd, "groups": {"cold(<5)": {"ndcg@20": cold}, "warm(5-20)": {"ndcg@20": nd},
                   "established(>20)": {"ndcg@20": nd}, "items_tail": {"recall@20_micro": tail},
                   "gini@20": .5, "coverage@20": .3}}, open(f"{r7}/ml1m/{m}_{sd}.json", "w"))
x = e78.collect(r7).query("method == 'X'").iloc[0]
assert abs(x.ndcg20_rel - 20) < 1e-6 and abs(x.ndcg20_cold_rel - 50) < 1e-6 and abs(x.recall20_tail_rel + 50) < 1e-6 and x.n_seeds == 2
# family baseline: T-CE is compared with Plain-BCE, not Plain-BPR
r8 = os.path.join(tmp, "r8"); os.makedirs(r8 + "/ml1m")
for m, nd in (("Plain-BPR", .10), ("Plain-BCE", .08), ("T-CE", .096)):
    json.dump({"dataset": "ml1m", "method": m, "backbone": "LightGCN", "cond": "N2_20", "seed": 1, "ndcg@20": nd,
               "recall@20": nd, "groups": {"gini@20": .5}}, open(f"{r8}/ml1m/{m}.json", "w"))
x = e78.collect(r8).query("method == 'T-CE'").iloc[0]
assert abs(x.ndcg20_rel + 4) < 1e-6 and abs(x.ndcg20_fam - 20) < 1e-6, (x.ndcg20_rel, x.ndcg20_fam)
print("ALL E2 TESTS PASSED")
