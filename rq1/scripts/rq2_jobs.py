"""RQ2 (lean) on PC 1: injected against natural noise at the dataset's own noise share rho*.

Design doc, RQ2: conditions Natural (N0 as collected), Random (clean base + N1), Popularity (clean base + N2),
Hard (clean base + N3), each with the same amount of noise rho*. Lean version (decided by Claude, 5 Nov 2026,
stated to the user; the full design does not fit before 3 Dec):
  * no re-tuning: every method keeps its Part C pick (tuned on clean validation, N0); the design re-tunes per condition
  * datasets Adressa, Yelp, Amazon-Book, ML-1M (KuaiRec was never prepared); 3 seeds; LightGCN only
  * methods: every Part C method that has a pick on the dataset, except LLaRD (its LLM knowledge is built per training
    file on PC 2) and SGDL (not in Part C); plus Plain-BPR and Plain-BCE. N0 and the oracle come from Part C.
Commands are exactly the Part C final commands (built with rq1kit.partc's own helpers) with another training file;
results go to results/RQ2/<dataset>/<run>.json with the tag part=RQ2.

rho* = share of proxy-noisy rows (noisy == 1) in train.tsv. rq1kit.noise injects rate x (clean positives of the
user), so the injected share is rate / (1 + rate); rate = rho* / (1 - rho*) gives every condition the share rho*.
Noise files are written as data/<ds>/train_RQ2<N1|N2|N3>_s<seed>.tsv (own names: they can never collide with
Part C's train_N2_20_s*.tsv).

  python scripts/rq2_jobs.py rho              # configs/rq2/rho.json
  python scripts/rq2_jobs.py prep             # MF-BPR on each clean base (top-K for N3), commands to run, one per line
  python scripts/rq2_jobs.py noise            # the 36 noise files (skips existing ones)
  python scripts/rq2_jobs.py jobs > configs/rq2/jobs.csv
"""
import csv
import json
import os
import sys

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT)

DATASETS = ["adressa", "ml1m", "yelp", "amazon_book"]      # fast first, so whole conditions finish early
CONDS = ["N1", "N2", "N3"]
SEEDS = [1, 2, 3]
SKIP_METHODS = {"llard"}
RHO = os.path.join(KIT, "configs/rq2/rho.json")


def kit_path(*p):
    return os.path.join(KIT, *p)


def train_file(cond, seed):
    return f"train_RQ2{cond}_s{seed}.tsv"


def cmd_rho():
    import pandas as pd
    out = {}
    for ds in DATASETS:
        tr = pd.read_csv(kit_path("data", ds, "train.tsv"), sep="\t", usecols=["noisy"])
        rho = float((tr["noisy"] == 1).mean())
        if not 0 < rho < 0.9:
            raise SystemExit(f"{ds}: natural noise share {rho:.4f} is outside (0, 0.9); check data/{ds}/train.tsv")
        out[ds] = {"rho_star": rho, "rate": rho / (1 - rho), "train_rows": int(len(tr)), "noisy_rows": int((tr["noisy"] == 1).sum())}
        print(f"{ds}: rho* {rho:.4f}, injection rate {rho / (1 - rho):.4f} ({out[ds]['noisy_rows']} of {len(tr)} rows)")
    os.makedirs(os.path.dirname(RHO), exist_ok=True)
    json.dump(out, open(RHO, "w"), indent=1)


def mf_dir(ds):
    return f"runs/rq2_prep/{ds}_mf_clean"


def cmd_prep():
    """One command per line: MF-BPR on the clean base of each dataset (tuned plain MF-BPR settings), for N3."""
    best = json.load(open(kit_path("configs/best_plain.json")))
    for ds in DATASETS:
        if os.path.isfile(kit_path(mf_dir(ds), "topk_valid.npy")):
            continue
        b = best[f"{ds}|mf|bpr"]
        print(f"python -m rq1kit.backbone --data data/{ds} --train_file train_clean.tsv --model mf --loss bpr "
              f"--lr {b['lr']} --reg {b['reg']} --seed 1 --run_dir {mf_dir(ds)}")


def cmd_noise():
    from rq1kit.noise import inject
    rho = json.load(open(RHO))
    for ds in DATASETS:
        for cond in CONDS:
            for s in SEEDS:
                path = kit_path("data", ds, train_file(cond, s))
                if os.path.isfile(path):
                    continue
                topk = kit_path(mf_dir(ds), "topk_valid.npy") if cond == "N3" else None
                if topk and not os.path.isfile(topk):
                    raise SystemExit(f"N3 needs {topk}: run the prep commands first")
                out, added = inject(kit_path("data", ds), cond, rho[ds]["rate"], s, topk)
                tmp = path + ".tmp"
                out[["user", "item", "noisy", "ts"]].to_csv(tmp, sep="\t", index=False)
                os.replace(tmp, path)
                print(f"{ds} {cond} s{s}: {len(added)} injected = {len(added) / len(out):.4f} of {len(out)} rows "
                      f"(rho* {rho[ds]['rho_star']:.4f})")


def jobs():
    from rq1kit import partc
    os.chdir(KIT)
    proto, methods = partc.load_protocol(), partc.load_methods()
    best_plain = partc.load_json(partc.BEST_PLAIN, {})
    rows = []
    for s in SEEDS:
        for ds in DATASETS:
            slots = proto["dataset_slots"].get(ds, 1)
            runs = [("plain", f"plain_lightgcn_{loss}", "rq1kit.backbone", f"--loss {loss}", loss, f"Plain-{loss.upper()}")
                    for loss in ("bpr", "bce")]
            for m in methods:
                if m["name"] in SKIP_METHODS or "lightgcn" not in m["backbones"] or ds not in m["datasets"]:
                    continue
                pick = (partc.load_json(os.path.join(partc.BEST_DIR, f"{m['name']}.json"), {}) or {}).get(ds)
                if not pick:
                    if s == SEEDS[0]:
                        print(f"note: {m['name']} has no pick on {ds}; left out", file=sys.stderr)
                    continue
                params = {k: pick[k] for k in m["grid"][0]}
                args = f"{m['base_args']} {partc.margs(params)}".strip()
                runs.append(("method", f"{m['name']}_lightgcn", m["module"], args, m["loss"], m["display"]))
            for cond in CONDS:
                tf = train_file(cond, s)
                for kind, stem, module, args, loss, display in runs:
                    bb = best_plain[f"{ds}|lightgcn|{loss}"]
                    name = f"{stem}_RQ2{cond}_s{s}"
                    rd, res = f"runs/rq2/{ds}/{name}", f"results/RQ2/{ds}/{name}.json"
                    extra = f" {proto['final_extra_args']}" if proto.get("final_extra_args") else ""
                    train = (f"python -m {module} {args} --data data/{ds} --train_file {tf}"
                             f" --model lightgcn --lr {bb['lr']} --reg {bb['reg']} "
                             f"--seed {s} --run_dir {rd}{extra}")
                    ev = (f"python -m rq1kit.evaluate --data data/{ds} --train_file {tf} --topk {rd}/topk_test.npy --out {res} "
                          f"--tag part=RQ2 dataset={ds} method={display} backbone=LightGCN cond=RQ2{cond} seed={s} train_file={tf}")
                    rows.append(dict(job_id=f"rq2_{ds}_{name}", cwd=".", cmd=f'bash -c "{train} && {ev}"', slots=slots))
    w = csv.DictWriter(sys.stdout, fieldnames=["job_id", "cwd", "cmd", "slots"])
    w.writeheader()
    w.writerows(rows)
    print(f"{len(rows)} RQ2 jobs", file=sys.stderr)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    {"rho": cmd_rho, "prep": cmd_prep, "noise": cmd_noise, "jobs": jobs}.get(what, lambda: sys.exit(__doc__))()
