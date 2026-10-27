"""Pick the best tuning trial per dataset, backbone and loss (highest validation NDCG@20 on clean validation).

  python scripts/pick_best.py --runs runs/tune --out configs/best_plain.json
"""
import argparse
import glob
import json
import os

ap = argparse.ArgumentParser()
ap.add_argument("--runs", default="runs/tune")
ap.add_argument("--out", default="configs/best_plain.json")
a = ap.parse_args()
best = {}
for f in glob.glob(os.path.join(a.runs, "*", "*", "run.json")):
    r = json.load(open(f))
    ds = os.path.basename(os.path.dirname(os.path.dirname(f)))
    key = f"{ds}|{r['model']}|{r['loss']}"
    if key not in best or r["best_valid_ndcg@20"] > best[key]["valid_ndcg@20"]:
        best[key] = {"lr": r["lr"], "reg": r["reg"], "valid_ndcg@20": r["best_valid_ndcg@20"], "best_epoch": r["best_epoch"],
                     "train_seconds": r["train_seconds"], "trial": os.path.basename(os.path.dirname(f))}
json.dump(best, open(a.out, "w"), indent=2, sort_keys=True)
for k, v in sorted(best.items()):
    print(k, v)
