"""RQ5 (lean) on PC 1: noise curves for the Part C methods on Yelp and Gowalla.

Design doc, RQ5: which family wins under which data; noise curves 0-50% for all core methods. Lean version (Claude,
21 Nov 2026, stated to the user; the full density x noise grid does not fit before 3 Dec):
  * popularity noise (N2) injected on the clean base at rate 10%, 30% and 50% (rate = injected rows per clean positive
    of the user, the same meaning as Part C's N2_20); Part C already holds 20% and N0, the oracle holds the clean point
  * datasets Yelp and Gowalla (the two sparse datasets with most room for denoisers); 3 seeds; LightGCN only
  * methods: every Part C method that has a pick on the dataset, except LLaRD (ML-1M only), plus Plain-BPR and Plain-BCE
  * no re-tuning: every method keeps its Part C pick (as in RQ2 lean)
Commands are the Part C final commands (rq1kit.partc's own helpers) with another training file; results go to
results/RQ5/<dataset>/<run>.json with the tag part=RQ5. Noise files are data/<ds>/train_RQ5N2_<pct>_s<seed>.tsv (own
names: they cannot collide with Part C's or RQ2's files).

KIT is the directory that holds data/, configs/ and rq1kit (default: the parent of scripts/; the PC1 queue sets it to
~/rq1-kit, because this file lives in the survey repo and runs against that kit).

  python scripts/rq5_jobs.py noise             # the noise files (skips existing ones)
  python scripts/rq5_jobs.py jobs > configs/rq5/jobs.csv
Environment: RQ5_LEVELS="10,30,50" (percent), RQ5_DATASETS="yelp,gowalla".
"""
import csv
import os
import sys

KIT = os.environ.get("KIT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT)

DATASETS = os.environ.get("RQ5_DATASETS", "yelp,gowalla").split(",")
LEVELS = [int(x) for x in os.environ.get("RQ5_LEVELS", "10,30,50").split(",")]
SEEDS = [1, 2, 3]
SKIP_METHODS = {"llard"}


def kit_path(*p):
    return os.path.join(KIT, *p)


def train_file(pct, seed):
    return f"train_RQ5N2_{pct}_s{seed}.tsv"


def cmd_noise():
    from rq1kit.noise import inject
    for ds in DATASETS:
        for pct in LEVELS:
            for s in SEEDS:
                path = kit_path("data", ds, train_file(pct, s))
                if os.path.isfile(path):
                    continue
                out, added = inject(kit_path("data", ds), "N2", pct / 100.0, s, None)
                tmp = path + ".tmp"
                out[["user", "item", "noisy", "ts"]].to_csv(tmp, sep="\t", index=False)
                os.replace(tmp, path)
                print(f"{ds} N2 {pct}% s{s}: {len(added)} injected = {len(added) / len(out):.4f} of {len(out)} rows")


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
            for pct in LEVELS:
                tf = train_file(pct, s)
                for kind, stem, module, args, loss, display in runs:
                    bb = best_plain[f"{ds}|lightgcn|{loss}"]
                    name = f"{stem}_RQ5N2_{pct}_s{s}"
                    rd, res = f"runs/rq5/{ds}/{name}", f"results/RQ5/{ds}/{name}.json"
                    extra = f" {proto['final_extra_args']}" if proto.get("final_extra_args") else ""
                    train = (f"python -m {module} {args} --data data/{ds} --train_file {tf}"
                             f" --model lightgcn --lr {bb['lr']} --reg {bb['reg']} "
                             f"--seed {s} --run_dir {rd}{extra}")
                    ev = (f"python -m rq1kit.evaluate --data data/{ds} --train_file {tf} --topk {rd}/topk_test.npy --out {res} "
                          f"--tag part=RQ5 dataset={ds} method={display} backbone=LightGCN cond=RQ5N2_{pct} seed={s} train_file={tf}")
                    rows.append(dict(job_id=f"rq5_{ds}_{name}", cwd=".", cmd=f'bash -c "{train} && {ev}"', slots=slots))
    w = csv.DictWriter(sys.stdout, fieldnames=["job_id", "cwd", "cmd", "slots"])
    w.writeheader()
    w.writerows(rows)
    print(f"{len(rows)} RQ5 jobs", file=sys.stderr)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    {"noise": cmd_noise, "jobs": jobs}.get(what, lambda: sys.exit(__doc__))()
