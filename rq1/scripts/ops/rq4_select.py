"""Helpers that let RQ4 run on more than one PC (scripts/rq4_run.sh). Job lists and picks are unchanged; this only
selects rows and moves picks between machines.

  python scripts/ops/rq4_select.py filter JOBS.csv --datasets ml1m,yelp [--seeds 1,2] [--timeout 4h] > JOBS_here.csv
  python scripts/ops/rq4_select.py split  configs/rq4/best.json yelp configs/rq4/picks_yelp.json
  python scripts/ops/rq4_select.py merge  configs/rq4/best.json PICKS.json yelp
  python scripts/ops/rq4_select.py check  PICKS.json yelp        # exit 0 only if every Yelp cell has a pick

Job ids: tuning rq4tune_<dataset>_..., finals rq4_<dataset>_<run>_s<seed>.
"""
import csv
import json
import os
import sys

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KIT, "scripts"))


def job_dataset(job_id):
    return job_id.split("_")[1]


def job_seed(job_id):
    last = job_id.rsplit("_", 1)[-1]
    return int(last[1:]) if last.startswith("s") and last[1:].isdigit() else None


def cmd_filter(path, datasets, seeds, timeout=None):
    rows = list(csv.DictReader(open(path)))
    if not rows:
        raise SystemExit(f"{path}: no jobs")
    keep = [r for r in rows if job_dataset(r["job_id"]) in datasets
            and (seeds is None or job_seed(r["job_id"]) is None or job_seed(r["job_id"]) in seeds)]
    if timeout:  # a job that hangs is killed (exit 124, SIGKILL 60 s later if needed) and counts as failed
        for r in keep:
            r["cmd"] = f"timeout -k 60 {timeout} {r['cmd']}"
    w = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(keep)
    print(f"{len(keep)} of {len(rows)} jobs kept (datasets {','.join(sorted(datasets))}"
          f"{', seeds ' + ','.join(map(str, sorted(seeds))) if seeds else ''})", file=sys.stderr)


def load(path):
    return json.load(open(path)) if os.path.isfile(path) else {}


def save(obj, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    json.dump(obj, open(tmp, "w"), indent=1, sort_keys=True)
    os.replace(tmp, path)


def cmd_split(best_path, ds, out):
    sub = {k: v for k, v in load(best_path).items() if k.startswith(ds + "|")}
    if not sub:
        raise SystemExit(f"no {ds} picks in {best_path}")
    save(sub, out)
    print(f"{len(sub)} {ds} picks -> {out}", file=sys.stderr)


def cmd_merge(best_path, picks_path, ds):
    best, extra = load(best_path), load(picks_path)
    add = {k: v for k, v in extra.items() if k.startswith(ds + "|")}
    if not add:
        raise SystemExit(f"no {ds} picks in {picks_path}")
    best = {k: v for k, v in best.items() if not k.startswith(ds + "|")}
    best.update(add)
    save(best, best_path)
    print(f"merged {len(add)} {ds} picks from {picks_path} into {best_path}", file=sys.stderr)


def cmd_check(picks_path, ds):
    import rq4_jobs
    want = {f"{ds}|{s}|{t}" for s, t in rq4_jobs.cells(ds)}
    have = set(load(picks_path))
    missing = sorted(want - have)
    print(f"{len(want & have)} of {len(want)} {ds} cells picked" + (f"; missing {missing[:5]}" if missing else ""))
    sys.exit(0 if not missing else 1)


def main():
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    if a[0] == "filter":
        opts = dict(zip(a[2::2], a[3::2]))
        seeds = {int(x) for x in opts["--seeds"].split(",")} if opts.get("--seeds") else None
        cmd_filter(a[1], set(opts["--datasets"].split(",")), seeds, opts.get("--timeout"))
    elif a[0] == "split":
        cmd_split(a[1], a[2], a[3])
    elif a[0] == "merge":
        cmd_merge(a[1], a[2], a[3])
    elif a[0] == "check":
        cmd_check(a[1], a[2])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
