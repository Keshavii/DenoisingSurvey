"""Gather every result JSON into tables for RQ1.

  python -m rq1kit.collect --results results --methods configs/methods.csv --reported configs/reported.csv --out tables

Writes:
  tables/all_runs.csv         one row per evaluated run
  tables/summary.csv          mean and std over seeds per dataset x backbone x condition x method,
                              with relative NDCG@20 gain over the plain backbone trained with the same loss
  tables/partB_scorecard.csv  reported vs reproduced numbers (needs reported.csv filled in)
"""
import argparse
import glob
import json
import os

import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results")
    ap.add_argument("--methods", default="configs/methods.csv")
    ap.add_argument("--reported", default="configs/reported.csv")
    ap.add_argument("--out", default="tables")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rows = []
    for f in glob.glob(os.path.join(a.results, "**", "*.json"), recursive=True):
        r = json.load(open(f))
        r.pop("groups", None)
        r["file"] = f
        rows.append(r)
    if not rows:
        print("no results yet")
        return
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(a.out, "all_runs.csv"), index=False)
    test = df[df["split"] == "test"].copy()
    meth = pd.read_csv(a.methods)
    test = test.merge(meth[["method", "loss", "family", "year"]], on="method", how="left")
    keys = ["part", "dataset", "backbone", "cond", "method"]
    agg = test.groupby(keys).agg(ndcg20=("ndcg@20", "mean"), ndcg20_std=("ndcg@20", "std"),
                                 recall20=("recall@20", "mean"), recall20_std=("recall@20", "std"),
                                 seeds=("seed", "nunique"), loss=("loss", "first"),
                                 family=("family", "first"), year=("year", "first")).reset_index()
    plain = agg[agg["method"].str.startswith("Plain")][["part", "dataset", "backbone", "cond", "loss", "ndcg20"]]
    plain = plain.rename(columns={"ndcg20": "plain_ndcg20"})
    agg = agg.merge(plain, on=["part", "dataset", "backbone", "cond", "loss"], how="left")
    agg["gain_pct"] = 100 * (agg["ndcg20"] / agg["plain_ndcg20"] - 1)
    # softmax-loss methods (Plain-SL, DrRL) are also shown against plain BPR, the kit's default reference
    bpr = plain[plain["loss"] == "bpr"].drop(columns="loss").rename(columns={"plain_ndcg20": "plain_bpr_ndcg20"})
    agg = agg.merge(bpr, on=["part", "dataset", "backbone", "cond"], how="left")
    agg["gain_vs_bpr_pct"] = 100 * (agg["ndcg20"] / agg["plain_bpr_ndcg20"] - 1)
    agg.to_csv(os.path.join(a.out, "summary.csv"), index=False)
    print(agg.to_string(index=False, max_rows=60))
    if os.path.exists(a.reported):
        rep = pd.read_csv(a.reported)
        b = agg[agg["part"] == "B"]
        sc = rep.merge(b, on=["method", "dataset", "backbone"], how="left")
        col = {"recall@20": "recall20", "ndcg@20": "ndcg20"}
        sc["reproduced"] = [r[col.get(r["metric"], "ndcg20")] if r["metric"] in col else None for _, r in sc.iterrows()]
        sc["gap_pct"] = 100 * (sc["reproduced"] / sc["reported_value"] - 1)
        sc.to_csv(os.path.join(a.out, "partB_scorecard.csv"), index=False)


if __name__ == "__main__":
    main()
