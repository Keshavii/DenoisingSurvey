"""E2 variant from Part C results: does the method ranking survive a shift in TRAINING noise (N0 -> N2_20)?

Reads results/C/<dataset>/*.json (the evaluator's output, tagged dataset, method, backbone, cond, seed), averages NDCG@20
over seeds, ranks methods per dataset and condition, and reports Kendall tau between the N0 and N2_20 rankings.
No training, no GPU.   python -m rq1kit.e2_shift --results results/C --backbone LightGCN --out results/E2/shift.json
"""
import argparse
import glob
import json
import os
from collections import defaultdict

from .e2 import kendall


def load(results, backbone):
    acc = defaultdict(list)
    for p in glob.glob(os.path.join(results, "*", "*.json")):
        r = json.load(open(p))
        if r.get("backbone") != backbone or "ndcg@20" not in r:
            continue
        acc[(r["dataset"], r["cond"], r["method"])].append(r["ndcg@20"])
    return {k: sum(v) / len(v) for k, v in acc.items()}


def shift(table, a="N0", b="N2_20"):
    out = {}
    for ds in sorted({k[0] for k in table}):
        ma = {k[2]: v for k, v in table.items() if k[0] == ds and k[1] == a}
        mb = {k[2]: v for k, v in table.items() if k[0] == ds and k[1] == b}
        common = sorted(set(ma) & set(mb))
        if len(common) < 3:
            continue
        out[ds] = dict(n_methods=len(common), tau=kendall([ma[m] for m in common], [mb[m] for m in common]),
                       best_a=max(common, key=ma.get), best_b=max(common, key=mb.get),
                       rank_a=sorted(common, key=lambda m: -ma[m]), rank_b=sorted(common, key=lambda m: -mb[m]),
                       pct_change={m: round(100 * (mb[m] / ma[m] - 1), 1) for m in common})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/C")
    ap.add_argument("--backbone", default="LightGCN")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = shift(load(a.results, a.backbone))
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=2)
    for ds, r in res.items():
        print(f"{ds}: {r['n_methods']} methods, tau={r['tau']:.2f}, best N0={r['best_a']}, best N2_20={r['best_b']}")
        print("   N0   :", " > ".join(r["rank_a"]))
        print("   N2_20:", " > ".join(r["rank_b"]))


if __name__ == "__main__":
    main()
