"""Part C batch 1, step 1: T-CE and R-CE (ADT) job lists for rq1kit.queue.

  python scripts/make_jobs_adt.py tune  > configs/jobs_tune_adt.csv     # 15 trials x 5 datasets, LightGCN, N0
  python scripts/make_jobs_adt.py pick                                  # -> configs/best_adt.json
  python scripts/make_jobs_adt.py final > configs/jobs_final_adt.csv    # 2 methods x 5 datasets x 3 seeds x 3 conditions

Protocol (same for every Part C method):
  * Backbone settings (lr, reg) are the tuned Plain-BCE values in configs/best_plain.json for the same dataset and backbone.
  * Method settings are tuned on LightGCN under N0 (one seed, at most 100 epochs), selected on clean-validation NDCG@20.
    Grids come from the ADT paper's search ranges: T-CE epsilon_max {0.05, 0.1, 0.2} x epsilon_N {1k, 10k, 30k}
    (8 combinations, (0.05, 1k) left out); R-CE beta {0.05, 0.1, 0.15, 0.2, 0.25, 0.5, 1.0} (all 7 values).
  * Final runs: the selected method settings, 3 seeds, LightGCN N0, LightGCN N2 20%, MF N0 (MF uses the LightGCN-tuned
    method settings with MF's own Plain-BCE lr and reg).
"""
import argparse
import csv
import glob
import itertools
import json
import os
import sys

DATASETS = ["adressa", "ml1m", "yelp", "gowalla", "amazon_book"]
SEEDS = [1, 2, 3]
BIG = {"amazon_book", "yelp", "gowalla"}
GRIDS = {
    "tce": [dict(drop_rate=d, num_gradual=g) for d, g in itertools.product([0.05, 0.1, 0.2], [1000, 10000, 30000])
            if (d, g) != (0.05, 1000)],
    "rce": [dict(alpha=b) for b in [0.05, 0.1, 0.15, 0.2, 0.25, 0.5, 1.0]],
}
NAME = {"tce": "T-CE", "rce": "R-CE"}


def margs(m, g):
    return " ".join(f"--{k} {v}" for k, v in g.items())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["tune", "pick", "final"])
    ap.add_argument("--data_root", default="data")
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--results", default="results")
    ap.add_argument("--best_plain", default="configs/best_plain.json")
    ap.add_argument("--best_adt", default="configs/best_adt.json")
    a = ap.parse_args()
    py = "python -m"
    plain = json.load(open(a.best_plain))
    rows = []
    if a.what == "tune":
        for ds, m in itertools.product(DATASETS, ["tce", "rce"]):
            b = plain[f"{ds}|lightgcn|bce"]
            for k, g in enumerate(GRIDS[m]):
                rd = os.path.join(a.runs, "tune_adt", ds, f"{m}_t{k}")
                rows.append(dict(job_id=f"tune_{ds}_{m}_t{k}", cwd=".", slots=2 if ds in BIG else 1,
                                 cmd=f"{py} rq1kit.adt --method {m} {margs(m, g)} --data {os.path.join(a.data_root, ds)} "
                                     f"--model lightgcn --lr {b['lr']} --reg {b['reg']} --epochs 100 --seed 0 --no_export --run_dir {rd}"))
    elif a.what == "pick":
        best = {}
        for f in glob.glob(os.path.join(a.runs, "tune_adt", "*", "*", "run.json")):
            r = json.load(open(f))
            ds = os.path.basename(os.path.dirname(os.path.dirname(f)))
            key = f"{ds}|{r['method']}"
            if key not in best or r["best_valid_ndcg@20"] > best[key]["valid_ndcg@20"]:
                g = {k: r[k] for k in (["drop_rate", "num_gradual"] if r["method"] == "tce" else ["alpha"])}
                best[key] = {**g, "valid_ndcg@20": r["best_valid_ndcg@20"], "best_epoch": r["best_epoch"],
                             "trial": os.path.basename(os.path.dirname(f))}
        n = {ds: sum(1 for f in glob.glob(os.path.join(a.runs, "tune_adt", ds, "*", "run.json"))) for ds in DATASETS}
        json.dump(best, open(a.best_adt, "w"), indent=2, sort_keys=True)
        for k, v in sorted(best.items()):
            print(k, v)
        print("finished trials per dataset (expect 15):", n)
        return
    else:
        best = json.load(open(a.best_adt))
        for ds, m, s in itertools.product(DATASETS, ["tce", "rce"], SEEDS):
            g = {k: v for k, v in best[f"{ds}|{m}"].items() if k in ("drop_rate", "num_gradual", "alpha")}
            for model, cond, tf in [("lightgcn", "N0", "train.tsv"), ("lightgcn", "N2_20", f"train_N2_20_s{s}.tsv"),
                                    ("mf", "N0", "train.tsv")]:
                b = plain[f"{ds}|{model}|bce"]
                name = f"{m}_{model}_{cond}_s{s}"
                rd = os.path.join(a.runs, ds, name)
                res = os.path.join(a.results, "C", ds, f"{name}.json")
                backbone = "LightGCN" if model == "lightgcn" else "MF-BPR"
                train = (f"{py} rq1kit.adt --method {m} {margs(m, g)} --data {os.path.join(a.data_root, ds)} --train_file {tf} "
                         f"--model {model} --lr {b['lr']} --reg {b['reg']} --seed {s} --run_dir {rd}")
                ev = (f"{py} rq1kit.evaluate --data {os.path.join(a.data_root, ds)} --train_file {tf} --topk {rd}/topk_test.npy "
                      f"--out {res} --tag part=C dataset={ds} method={NAME[m]} backbone={backbone} cond={cond} seed={s} "
                      f"train_file={tf}")
                rows.append(dict(job_id=f"{ds}_{name}", cwd=".", slots=2 if ds in BIG else 1, cmd=f"bash -c \"{train} && {ev}\""))
    w = csv.DictWriter(sys.stdout, fieldnames=["job_id", "cwd", "cmd", "slots"])
    w.writeheader()
    w.writerows(rows)


if __name__ == "__main__":
    main()
