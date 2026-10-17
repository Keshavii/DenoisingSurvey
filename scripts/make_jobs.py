"""Write job lists (CSV) for rq1kit.queue.

  python scripts/make_jobs.py noise       --data_root data                  > configs/jobs_noise.csv
  python scripts/make_jobs.py tune-plain  --data_root data --runs runs      > configs/jobs_tune_plain.csv
  python scripts/pick_best.py --runs runs/tune --out configs/best_plain.json
  python scripts/make_jobs.py final-plain --data_root data --runs runs --best configs/best_plain.json > configs/jobs_plain.csv

Lean RQ1 matrix for the plain backbones and the oracle (Step 4 of the runbook):
  LightGCN x {BPR, BCE} x {N0, N2 20%} x 5 datasets x 3 seeds        = 60 runs
  MF       x {BPR, BCE} x {N0}         x 5 datasets x 3 seeds        = 30 runs
  Oracle: LightGCN x {BPR, BCE} on train_clean x 4 datasets x 3 seeds = 24 runs (Gowalla has no natural noise, so N0 is its oracle)
Tuning: 8 settings (lr x reg) per dataset, backbone and loss, under N0, one seed, at most 100 epochs = 160 trials.
"""
import argparse
import csv
import itertools
import json
import os
import sys

DATASETS = ["adressa", "ml1m", "yelp", "gowalla", "amazon_book"]  # smallest first
SEEDS = [1, 2, 3]
GRID = [{"lr": lr, "reg": reg} for lr, reg in itertools.product([1e-3, 5e-3], [1e-5, 1e-4, 1e-3, 1e-2])]
BIG = {"amazon_book", "yelp", "gowalla"}  # give these the whole GPU


def slots(ds):
    return 2 if ds in BIG else 1


def out(rows):
    w = csv.DictWriter(sys.stdout, fieldnames=["job_id", "cwd", "cmd", "slots"])
    w.writeheader()
    w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["noise", "tune-plain", "final-plain"])
    ap.add_argument("--data_root", default="data")
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--results", default="results")
    ap.add_argument("--best", default="configs/best_plain.json")
    ap.add_argument("--kit", default=".")
    a = ap.parse_args()
    py = "python -m"
    rows = []
    if a.what == "noise":
        for ds in DATASETS:
            d = os.path.join(a.data_root, ds)
            rows.append(dict(job_id=f"noise_{ds}_clean", cwd=a.kit, cmd=f"{py} rq1kit.noise --data {d} --cond clean", slots=1))
            for s in SEEDS:
                rows.append(dict(job_id=f"noise_{ds}_N2_20_s{s}", cwd=a.kit,
                                 cmd=f"{py} rq1kit.noise --data {d} --cond N2 --rate 0.2 --seed {s}", slots=1))
    elif a.what == "tune-plain":
        for ds, model, loss in itertools.product(DATASETS, ["lightgcn", "mf"], ["bpr", "bce"]):
            for k, g in enumerate(GRID):
                rd = os.path.join(a.runs, "tune", ds, f"{model}_{loss}_t{k}")
                rows.append(dict(job_id=f"tune_{ds}_{model}_{loss}_t{k}", cwd=a.kit, slots=slots(ds),
                                 cmd=f"{py} rq1kit.backbone --data {os.path.join(a.data_root, ds)} --model {model} --loss {loss} "
                                     f"--lr {g['lr']} --reg {g['reg']} --epochs 100 --seed 0 --no_export --run_dir {rd}"))
    else:
        best = json.load(open(a.best))
        plan = []
        for ds, loss, s in itertools.product(DATASETS, ["bpr", "bce"], SEEDS):
            plan.append((ds, "lightgcn", loss, "N0", "train.tsv", s))
            plan.append((ds, "lightgcn", loss, "N2_20", f"train_N2_20_s{s}.tsv", s))
            plan.append((ds, "mf", loss, "N0", "train.tsv", s))
            if ds != "gowalla":
                plan.append((ds, "lightgcn", loss, "oracle", "train_clean.tsv", s))
        for ds, model, loss, cond, tf, s in plan:
            g = best[f"{ds}|{model}|{loss}"]
            name = f"plain_{model}_{loss}_{cond}_s{s}"
            rd = os.path.join(a.runs, ds, name)
            method = ("Oracle-" if cond == "oracle" else "Plain-") + loss.upper()
            backbone = "LightGCN" if model == "lightgcn" else "MF-BPR"
            res = os.path.join(a.results, "C", ds, f"{name}.json")
            train = (f"{py} rq1kit.backbone --data {os.path.join(a.data_root, ds)} --train_file {tf} --model {model} "
                     f"--loss {loss} --lr {g['lr']} --reg {g['reg']} --seed {s} --run_dir {rd}")
            ev = (f"{py} rq1kit.evaluate --data {os.path.join(a.data_root, ds)} --train_file {tf} --topk {rd}/topk_test.npy "
                  f"--out {res} --tag part=C dataset={ds} method={method} backbone={backbone} "
                  f"cond={'N0' if cond == 'oracle' else cond} seed={s} train_file={tf}")
            rows.append(dict(job_id=f"{ds}_{name}", cwd=a.kit, slots=slots(ds), cmd=f"bash -c \"{train} && {ev}\""))
    out(rows)


if __name__ == "__main__":
    main()
