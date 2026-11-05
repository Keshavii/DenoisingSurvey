"""RQ10 stage 2: one table of full-ranking Recall@10 / NDCG@10 for every specialist run (leave-one-out, all items).

Sources (each code base's own full-ranking evaluation, or our wrapper where it has none):
  FMLP-Rec  logs/run_s2_fmlp_<name>.log: the last result dict ({'Epoch': 0, 'HIT@10': ...}, test, --full_sort).
            With one test item per user, HIT@10 is Recall@10.
  HSD       repos/hsd/results/hsd_<name>_SASRec.json (RecBole full ranking; hit@10 = Recall@10)
  STEAM     results/s2_steam_<name>.json (steam_full_eval.py; 'reported' = corrected sequence, STEAM's prediction)

  python rq10_collect.py --root ~/survey/rq10      # writes results/stage2_summary.tsv and prints it
"""
import argparse
import ast
import glob
import json
import os
import re

ap = argparse.ArgumentParser()
ap.add_argument("--root", default=os.path.expanduser("~/survey/rq10"))
a = ap.parse_args()
NAME = re.compile(r"^(?P<ds>.+)_(?P<lv>N0|I10|I20)_s(?P<seed>\d+)$")
rows = []


def add(method, name, recall, ndcg, src):
    m = NAME.match(name)
    if not m:
        return
    rows.append(dict(method=method, dataset=m["ds"], level=m["lv"], seed=int(m["seed"]),
                     recall10=float(recall), ndcg10=float(ndcg), source=os.path.relpath(src, a.root)))


for log in glob.glob(os.path.join(a.root, "logs", "run_s2_fmlp_*.log")):
    if not os.path.isfile(log.replace(".log", ".done")):
        continue
    last = None
    for line in open(log, errors="replace"):
        line = line.strip()
        if line.startswith("{") and "'HIT@10'" in line:
            try:
                last = ast.literal_eval(line)
            except (ValueError, SyntaxError):
                pass
    name = None
    for line in open(log, errors="replace"):
        hit = re.search(r"data_name='([^']+)'", line)
        if hit:
            name = hit.group(1)
            break
    if last and name:
        add("FMLP-Rec", name, last["HIT@10"], last["NDCG@10"], log)

for f in glob.glob(os.path.join(a.root, "repos", "hsd", "results", "hsd_*_SASRec.json")):
    r = json.load(open(f))
    t = {k.lower(): v for k, v in r.get("test_result", {}).items()}
    if "hit@10" in t and "ndcg@10" in t:
        keep = os.path.join(a.root, "results", f"s2_hsd_{r['dataset']}.json")   # results/ is published; repos/ is not
        if NAME.match(r["dataset"]):
            os.makedirs(os.path.dirname(keep), exist_ok=True)
            json.dump(r, open(keep, "w"), indent=1)
        add("HSD (SASRec)", r["dataset"], t["hit@10"], t["ndcg@10"], keep if os.path.isfile(keep) else f)

for f in glob.glob(os.path.join(a.root, "results", "s2_steam_*.json")):
    r = json.load(open(f))
    name = os.path.basename(f)[len("s2_steam_"):-len(".json")]
    add("STEAM", name, r["reported"]["recall@10"], r["reported"]["ndcg@10"], f)

rows.sort(key=lambda r: (r["dataset"], r["method"], r["seed"], ["N0", "I10", "I20"].index(r["level"])))
out = os.path.join(a.root, "results", "stage2_summary.tsv")
os.makedirs(os.path.dirname(out), exist_ok=True)
cols = ["method", "dataset", "level", "seed", "recall10", "ndcg10", "source"]
with open(out, "w") as f:
    f.write("\t".join(cols) + "\n")
    for r in rows:
        f.write("\t".join(f"{r[c]:.4f}" if isinstance(r[c], float) else str(r[c]) for c in cols) + "\n")
print(f"{len(rows)} runs -> {out}")
for r in rows:
    print(f"  {r['method']:13} {r['dataset']:20} {r['level']:4} s{r['seed']}  Recall@10 {r['recall10']:.4f}  NDCG@10 {r['ndcg10']:.4f}")
