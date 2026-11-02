"""E7 (popularity bias x denoising) and E8 (cold-start x noise) from Part C result files. No training, no GPU.

Reads results/C/<dataset>/*.json (evaluator output with a "groups" block), averages over seeds and writes one tidy CSV:
  dataset, method, backbone, cond, n_seeds, ndcg20, recall20,
  E8: ndcg20_cold, ndcg20_warm, ndcg20_established     (user groups by training history: <5, 5-20, >20)
  E7: recall20_head, recall20_mid, recall20_tail       (micro recall@20 on truth items by item popularity tertile)
      coverage20, gini20                               (exposure concentration of the top-20 lists)
and *_rel columns: the same number as a % change against Plain-BPR in the same dataset, backbone and condition.
   python -m rq1kit.e78 --results results/C --out results/E78/e78.csv
"""
import argparse
import glob
import json
import os
from collections import defaultdict

import pandas as pd

COLS = {
    "ndcg@20": ("ndcg20", lambda r: r["ndcg@20"]),
    "recall@20": ("recall20", lambda r: r["recall@20"]),
    "cold": ("ndcg20_cold", lambda r: r["groups"].get("cold(<5)", {}).get("ndcg@20")),
    "warm": ("ndcg20_warm", lambda r: r["groups"].get("warm(5-20)", {}).get("ndcg@20")),
    "est": ("ndcg20_established", lambda r: r["groups"].get("established(>20)", {}).get("ndcg@20")),
    "head": ("recall20_head", lambda r: r["groups"].get("items_head", {}).get("recall@20_micro")),
    "mid": ("recall20_mid", lambda r: r["groups"].get("items_mid", {}).get("recall@20_micro")),
    "tail": ("recall20_tail", lambda r: r["groups"].get("items_tail", {}).get("recall@20_micro")),
    "cov": ("coverage20", lambda r: r["groups"].get("coverage@20")),
    "gini": ("gini20", lambda r: r["groups"].get("gini@20")),
}
BASELINE = "Plain-BPR"


def collect(results):
    acc = defaultdict(lambda: defaultdict(list))
    for p in glob.glob(os.path.join(results, "*", "*.json")):
        r = json.load(open(p))
        if "groups" not in r or "method" not in r:
            continue
        key = (r["dataset"], r["method"], r["backbone"], r["cond"])
        acc[key]["seed"].append(r.get("seed"))
        for _, (name, fn) in COLS.items():
            v = fn(r)
            if v is not None:
                acc[key][name].append(v)
    rows = []
    for (ds, m, bb, cond), d in acc.items():
        row = dict(dataset=ds, method=m, backbone=bb, cond=cond, n_seeds=len(d["seed"]))
        for name in [n for n, _ in COLS.values()]:
            row[name] = sum(d[name]) / len(d[name]) if d.get(name) else None
        rows.append(row)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    base = df[df.method == BASELINE].set_index(["dataset", "backbone", "cond"])
    for name in [n for n, _ in COLS.values()]:
        rel = []
        for _, r in df.iterrows():
            k = (r.dataset, r.backbone, r.cond)
            b = base[name].get(k) if k in base.index else None
            rel.append(None if b in (None,) or pd.isna(b) or b == 0 or pd.isna(r[name]) else 100 * (r[name] / b - 1))
        df[name + "_rel"] = rel
    return df.sort_values(["dataset", "backbone", "cond", "method"]).reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/C")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    df = collect(a.results)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    df.to_csv(a.out, index=False)
    sel = df[(df.backbone == "LightGCN") & (df.cond == "N2_20")]
    for ds, g in sel.groupby("dataset"):
        print(f"\n{ds}  LightGCN, 20% injected noise: % change vs {BASELINE}")
        print(g[["method", "ndcg20_rel", "ndcg20_cold_rel", "ndcg20_established_rel", "recall20_tail_rel", "gini20"]]
              .round(1).to_string(index=False))


if __name__ == "__main__":
    main()
