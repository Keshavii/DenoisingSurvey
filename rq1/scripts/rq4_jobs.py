"""RQ4 job lists for rq1kit.queue (spec: Plan of Action doc, "RQ4 specification", final design of 4 Nov 2026).

  python scripts/rq4_jobs.py tune  > configs/rq4/jobs_tune.csv     # 3 trials per cell, N0, seed 0, 100 epochs
  python scripts/rq4_jobs.py pick                                   # best trial per cell -> configs/rq4/best.json
  python scripts/rq4_jobs.py final > configs/rq4/jobs_final.csv    # picked cells x conditions x seeds + references
  python scripts/rq4_jobs.py count                                  # job counts

Backbone learning rate and regularisation are the tuned Plain-BCE values (configs/best_plain.json).
"""
import csv
import json
import os
import sys

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Detection methods: signal only and signal + foundation, in matched pairs (same measurement, anchor added)
DET_ML = ["L1", "M1", "M2", "M1c", "L2", "L5", "L3", "L4", "P1", "P2", "R1", "R2", "R3", "R4", "R5"]
DET_YELP = [d for d in DET_ML if d not in ("R4", "R5")]          # no item text
PAIRS = ["L1", "M1", "L3", "L4", "R1", "R2"]                      # the three exact pairs (Blocks 2 and 3)
GRID = {"drop": ("rate", [0.05, 0.1, 0.2]), "reweight": ("beta", [0.25, 0.5, 1.0]),
        "relabel": ("rate", [0.05, 0.1, 0.2]), "resample": ("temp", [0.05, 0.1, 0.2]),
        # variants from other families (sheet page 1): graph pruning and graph edge weights (RGCF, DA-MRS, DeMBR,
        # LLaRD), user-level reweighting (UDT), soft labels (CSRec, GUIDER)
        "graph_drop": ("rate", [0.05, 0.1, 0.2]), "graph_reweight": ("beta", [0.25, 0.5, 1.0]),
        "user_reweight": ("beta", [0.25, 0.5, 1.0]), "soft_relabel": ("lam", [0.3, 0.5, 0.8]),
        # reshaping (SGL-ED contrastive views), random or signal-guided
        "reshape": ("ssl_reg", [0.05, 0.1, 0.5])}
CORE_TREATS = ["drop", "reweight", "relabel", "resample"]
VARIANT_TREATS = ["graph_drop", "graph_reweight", "user_reweight", "soft_relabel"]
DATASETS = {
    # detection methods, conditions (name -> training file pattern), seeds, queue slots per job
    "ml1m": dict(det=DET_ML, seeds=[1, 2, 3], slots=1,
                 conds={"N0": "train.tsv", "N1_20": "train_N1_20_s{seed}.tsv", "N3_20": "train_N3_20_s{seed}.tsv"}),
    "yelp": dict(det=DET_YELP, seeds=[1, 2], slots=2,
                 conds={"N0": "train.tsv", "N3_20": "train_N3_20_s{seed}.tsv"}),
}
TUNE_DIR, FINAL_DIR, RES_DIR = "runs/rq4_tune", "runs/rq4", "results/RQ4"
BEST = os.path.join(KIT, "configs/rq4/best.json")


def plain(ds):
    b = json.load(open(os.path.join(KIT, "configs/best_plain.json")))[f"{ds}|lightgcn|bce"]
    return b["lr"], b["reg"]


def cells(ds):
    """Block 1: every detection method x the 4 core treatments. Block 2: the exact pairs x the 4 variant
    treatments. Block 3: the exact pairs x signal-guided reshape, plus reshape with no detection."""
    det = DATASETS[ds]["det"]
    return ([(d, t) for d in det for t in CORE_TREATS] + [(d, t) for d in PAIRS for t in VARIANT_TREATS] +
            [(d, "reshape") for d in PAIRS] + [("none", "reshape")])


def tune_jobs():
    out = []
    for ds, d in DATASETS.items():
        lr, reg = plain(ds)
        for s, t in cells(ds):
            key, vals = GRID[t]
            for k, v in enumerate(vals):
                rd = f"{TUNE_DIR}/{ds}/{s}_{t}_t{k}"
                cmd = (f"python -m rq1kit.rq4 --signal {s} --treat {t} --{key} {v} --data data/{ds} --lr {lr} --reg {reg} "
                       f"--epochs 100 --seed 0 --no_export --run_dir {rd}")
                out.append(dict(job_id=f"rq4tune_{ds}_{s}_{t}_t{k}", cwd=".", cmd=cmd, slots=d["slots"]))
    return out


def pick(root=KIT):
    best, missing = {}, []
    for ds in DATASETS:
        for s, t in cells(ds):
            key, vals = GRID[t]
            trials = []
            for k, v in enumerate(vals):
                p = os.path.join(root, TUNE_DIR, ds, f"{s}_{t}_t{k}", "run.json")
                if os.path.isfile(p):
                    trials.append((json.load(open(p))["best_valid_ndcg@20"], k, v))
            if len(trials) < len(vals):
                missing.append(f"{ds}|{s}|{t} ({len(trials)}/{len(vals)})")
            if trials:
                val, k, v = max(trials)
                best[f"{ds}|{s}|{t}"] = {key: v, "trial": k, "valid_ndcg@20": val, "complete": len(trials) == len(vals)}
    return best, missing


def final_jobs(best):
    out = []
    for ds, d in DATASETS.items():
        lr, reg = plain(ds)
        for seed in d["seeds"]:
            for cond, pat in d["conds"].items():
                tf = pat.format(seed=seed)
                runs = [("plain", "none", "none", "")]
                runs += [(f"{s}_{t}", s, t, f" --{GRID[t][0]} {best[f'{ds}|{s}|{t}'][GRID[t][0]]}")
                         for s, t in cells(ds) if f"{ds}|{s}|{t}" in best]
                for name, s, t, extra in runs:
                    out.append(job(ds, name, s, t, extra, cond, tf, seed, lr, reg, d["slots"]))
            out.append(job(ds, "oracle", "none", "none", "", "clean", "train_clean.tsv", seed, lr, reg, d["slots"]))
    return out


def job(ds, name, s, t, extra, cond, tf, seed, lr, reg, slots):
    rid = f"{name}_{cond}_s{seed}"
    rd, res = f"{FINAL_DIR}/{ds}/{rid}", f"{RES_DIR}/{ds}/{rid}.json"
    train = (f"python -m rq1kit.rq4 --signal {s} --treat {t}{extra} --data data/{ds} --train_file {tf} --lr {lr} "
             f"--reg {reg} --seed {seed} --run_dir {rd}")
    ev = (f"python -m rq1kit.evaluate --data data/{ds} --train_file {tf} --topk {rd}/topk_test.npy --out {res} --tag "
          f"part=RQ4 dataset={ds} signal={s} treat={t} cond={cond} seed={seed} train_file={tf}")
    return dict(job_id=f"rq4_{ds}_{rid}", cwd=".", cmd=f'bash -c "{train} && {ev}"', slots=slots)


def write(rows):
    w = csv.DictWriter(sys.stdout, fieldnames=["job_id", "cwd", "cmd", "slots"])
    w.writeheader()
    w.writerows(rows)


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "count"
    if what == "tune":
        write(tune_jobs())
    elif what == "pick":
        best, missing = pick()
        os.makedirs(os.path.dirname(BEST), exist_ok=True)
        json.dump(best, open(BEST, "w"), indent=1, sort_keys=True)
        print(f"{len(best)} cells picked -> {BEST}; incomplete: {', '.join(missing) or 'none'}", file=sys.stderr)
    elif what == "final":
        write(final_jobs(json.load(open(BEST))))
    else:
        t = tune_jobs()
        f = final_jobs({f"{ds}|{s}|{x}": {GRID[x][0]: GRID[x][1][0]} for ds in DATASETS for s, x in cells(ds)})
        for ds in DATASETS:
            print(ds, "cells", len(cells(ds)), "tuning", sum(j["job_id"].startswith(f"rq4tune_{ds}_") for j in t),
                  "finals", sum(j["job_id"].startswith(f"rq4_{ds}_") for j in f))


if __name__ == "__main__":
    main()
