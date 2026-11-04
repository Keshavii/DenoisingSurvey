"""
RQ10 sequential noise injection.

For each source dataset (Beauty, Sports, Yelp) already in STEAM format, produces
N0 (clean copy), N2_20 (20 % random noise) and N3_30 (30 % random noise) variants
in both STEAM and RecBole-atomic formats so all sequential specialists use
the same data under the same noise conditions.

STEAM format (inferred from main.py argparse and SASRec convention):
  train.dat  — lines of "user_id item_id" (1-indexed), one interaction per line,
               in temporal order per user (users not necessarily contiguous).
               OR  "user_id item_1 item_2 … item_n" (one row per user, sequence).
               Detected automatically from the first line.
  valid.dat  — same format, leave-one-out validation item (second-to-last).
  test.dat   — same format, leave-one-out test item (last interaction).
  valid_neg.dat  — "user_id neg_1 neg_2 … neg_100" (100 sampled negatives per user).
  test_neg.dat   — same.

RecBole 1.0.1 atomic format:
  <dataset>.inter  — TSV with header "user_id:token\titem_id:token\ttimestamp:float"

Noise model (sequential, matches RQ1):
  Add floor(len(train_seq) * ratio) random (user, item) pairs drawn uniformly
  from items in the training set, inserted at a random position in the user's sequence.
  Items are drawn without replacement from the global item pool.
  Seed = 42 + noise_level (reproducible; different level → different draw).

Usage:
  python noise_inject.py --src_root ~/survey/rq10/repos/steam \
                         --dst_root ~/survey/rq10/data \
                         --datasets Beauty Sports Yelp \
                         --levels N0 N2_20 N3_30
  # For RecBole output add: --also_recbole
  # Dry run (no write): --dry_run
"""
import argparse, os, random, collections, shutil
from pathlib import Path

NOISE_RATIO = {"N0": 0.0, "N2_20": 0.20, "N3_30": 0.30}


# ── format detection ──────────────────────────────────────────────────────────

def detect_format(dat_path: Path):
    """Return 'pair' (user item per line) or 'seq' (user item1 item2…)."""
    with open(dat_path) as f:
        line = f.readline().strip()
    parts = line.split()
    if len(parts) == 2:
        return "pair"
    if len(parts) > 2:
        return "seq"
    raise ValueError(f"Cannot detect format from: {line!r}")


# ── readers ───────────────────────────────────────────────────────────────────

def read_pair(path: Path):
    """Return dict[user_id -> list[item_id]], order = file order."""
    seqs = collections.OrderedDict()
    with open(path) as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            u, i = ln.split()
            seqs.setdefault(u, []).append(i)
    return seqs


def read_seq(path: Path):
    """Return dict[user_id -> list[item_id]], from 'u i1 i2 …' lines."""
    seqs = collections.OrderedDict()
    with open(path) as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            parts = ln.split()
            seqs[parts[0]] = parts[1:]
    return seqs


def read_neg(path: Path):
    """Return dict[user_id -> list[neg_item_id]]."""
    negs = {}
    with open(path) as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            parts = ln.split()
            negs[parts[0]] = parts[1:]
    return negs


# ── writers ───────────────────────────────────────────────────────────────────

def write_pair(seqs, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for u, items in seqs.items():
            for i in items:
                f.write(f"{u} {i}\n")


def write_seq(seqs, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for u, items in seqs.items():
            f.write(u + " " + " ".join(items) + "\n")


def write_neg(negs, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for u, items in negs.items():
            f.write(u + " " + " ".join(items) + "\n")


def write_recbole(seqs, name: str, out_dir: Path):
    """Write RecBole 1.0.1 atomic .inter file (all training interactions)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.inter"
    with open(path, "w") as f:
        f.write("user_id:token\titem_id:token\ttimestamp:float\n")
        for u, items in seqs.items():
            for t, i in enumerate(items):
                f.write(f"{u}\t{i}\t{t}\n")  # synthetic timestamp = position
    return path


# ── noise injection ───────────────────────────────────────────────────────────

def inject_noise(train_seqs, ratio: float, seed: int):
    """Add floor(len(seq)*ratio) random items to each user's training sequence.
    Returns new dict with augmented sequences."""
    if ratio == 0.0:
        return {u: list(items) for u, items in train_seqs.items()}
    rng = random.Random(seed)
    all_items = list({i for items in train_seqs.values() for i in items})
    noisy = {}
    for u, items in train_seqs.items():
        n_add = max(1, int(len(items) * ratio))
        extra = rng.choices(all_items, k=n_add)
        combined = list(items)
        for item in extra:
            pos = rng.randint(0, len(combined))
            combined.insert(pos, item)
        noisy[u] = combined
    return noisy


# ── main ─────────────────────────────────────────────────────────────────────

def process_dataset(dataset, src_root, dst_root, levels, also_recbole, fmt, dry_run):
    src = Path(src_root) / dataset
    if not src.exists():
        print(f"  [skip] {dataset}: not found at {src}")
        return

    # Read source
    rf = read_seq if fmt == "seq" else read_pair
    train = rf(src / "train.dat")
    # valid and test: leave-one-out items (not modified by noise)
    valid_path = src / "valid.dat"
    test_path  = src / "test.dat"
    vneg_path  = src / "valid_neg.dat"
    tneg_path  = src / "test_neg.dat"
    valid = rf(valid_path)   if valid_path.exists()  else None
    test  = rf(test_path)    if test_path.exists()   else None
    vneg  = read_neg(vneg_path) if vneg_path.exists() else None
    tneg  = read_neg(tneg_path) if tneg_path.exists() else None

    for level in levels:
        ratio = NOISE_RATIO[level]
        seed  = 42 + int(level.split("_")[-1]) if "_" in level else 42
        noisy_train = inject_noise(train, ratio, seed)
        dst = Path(dst_root) / f"{dataset}_{level}"

        print(f"  {dataset}/{level}: {sum(len(v) for v in train.values())} "
              f"-> {sum(len(v) for v in noisy_train.values())} interactions")

        if dry_run:
            continue

        wf = write_seq if fmt == "seq" else write_pair
        wf(noisy_train, dst / "train.dat")
        if valid is not None: wf(valid, dst / "valid.dat")
        if test  is not None: wf(test,  dst / "test.dat")
        if vneg  is not None: write_neg(vneg, dst / "valid_neg.dat")
        if tneg  is not None: write_neg(tneg, dst / "test_neg.dat")

        if also_recbole:
            rb_dir = Path(dst_root) / "recbole" / f"{dataset}_{level}"
            write_recbole(noisy_train, f"{dataset}_{level}", rb_dir)
            # RecBole also needs .user and .item files for sequential models
            upath = rb_dir / f"{dataset}_{level}.user"
            ipath = rb_dir / f"{dataset}_{level}.item"
            users = list(noisy_train.keys())
            items = list({i for s in noisy_train.values() for i in s})
            with open(upath, "w") as f:
                f.write("user_id:token\n")
                for u in users: f.write(u + "\n")
            with open(ipath, "w") as f:
                f.write("item_id:token\n")
                for i in items: f.write(i + "\n")
            print(f"    RecBole -> {rb_dir}")

        print(f"    STEAM  -> {dst}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src_root", required=True,
                    help="Directory containing Beauty/, Sports/, Yelp/ in STEAM format")
    ap.add_argument("--dst_root", required=True,
                    help="Output root; writes <dataset>_<level>/ subdirs here")
    ap.add_argument("--datasets", nargs="+", default=["Beauty","Sports","Yelp"])
    ap.add_argument("--levels",   nargs="+", default=["N0","N2_20","N3_30"],
                    choices=list(NOISE_RATIO))
    ap.add_argument("--also_recbole", action="store_true",
                    help="Also write RecBole atomic format under dst_root/recbole/")
    ap.add_argument("--fmt", choices=["pair","seq","auto"], default="auto",
                    help="Force format; auto detects from train.dat first line")
    ap.add_argument("--dry_run", action="store_true")
    args = ap.parse_args()

    for ds in args.datasets:
        src = Path(args.src_root) / ds
        if args.fmt == "auto":
            td = src / "train.dat"
            if td.exists():
                fmt = detect_format(td)
                print(f"{ds}: detected format={fmt}")
            else:
                print(f"{ds}: train.dat missing, skip")
                continue
        else:
            fmt = args.fmt
        process_dataset(ds, args.src_root, args.dst_root,
                        args.levels, args.also_recbole, fmt, args.dry_run)


if __name__ == "__main__":
    main()
