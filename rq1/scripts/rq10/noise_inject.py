"""
RQ10 sequential noise injection.

Handles two source formats found in the repos:

  steam_csv  — STEAM format: each line is the full item sequence for one user,
               comma-separated, implicit user ID = line index (1-based).
               e.g.  4,5,2            (user 1: items 4, 5, 2)
               Files: train.dat, valid.dat, test.dat, valid_neg.dat, test_neg.dat

  fmlp       — FMLP-Rec format: each line is  user_id item1 item2 …
               space-separated, explicit user ID in column 0.
               e.g.  1 3408 9109 8050 …
               Files: <Dataset>.txt   (single file; no train/valid/test split)

Noise model (N2_20 = 20 %, N3_30 = 30 %):
  For each user's training sequence, insert floor(len × ratio) random items
  drawn uniformly from the global item pool, at random positions.
  Seed = 42 + noise_pct (reproducible; N2_20 → seed 62, N3_30 → seed 72).

Usage:
  # STEAM format (Beauty, Sports, Yelp already in repos/steam/)
  python noise_inject.py \
      --mode steam \
      --src_root ~/survey/rq10/repos/steam \
      --dst_root ~/survey/rq10/data \
      --datasets Beauty Sports Yelp \
      --levels N0 N2_20 N3_30

  # FMLP format (Beauty.txt in repos/fmlp/data/)
  python noise_inject.py \
      --mode fmlp \
      --src_root ~/survey/rq10/repos/fmlp/data \
      --dst_root ~/survey/rq10/repos/fmlp/data \
      --datasets Beauty \
      --levels N0 N2_20 N3_30
"""
import argparse, random, collections
from pathlib import Path

NOISE_RATIO = {"N0": 0.0, "N2_20": 0.20, "N3_30": 0.30}
NOISE_SEED  = {"N0": 42,  "N2_20": 62,   "N3_30": 72}


# ── readers ───────────────────────────────────────────────────────────────────

def read_steam_csv(path: Path):
    """STEAM: each line = comma-separated items; user = line index (1-based)."""
    seqs = collections.OrderedDict()
    with open(path) as f:
        for idx, ln in enumerate(f, 1):
            items = [x.strip() for x in ln.strip().split(',') if x.strip()]
            if items:
                seqs[str(idx)] = items
    return seqs


def read_fmlp(path: Path):
    """FMLP: each line = user_id item1 item2 … (space-separated)."""
    seqs = collections.OrderedDict()
    with open(path) as f:
        for ln in f:
            parts = ln.strip().split()
            if len(parts) >= 2:
                seqs[parts[0]] = parts[1:]
    return seqs


# ── writers ───────────────────────────────────────────────────────────────────

def write_steam_csv(seqs, path: Path):
    """Write comma-separated item sequences, one per line (user = line index)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        for items in seqs.values():
            f.write(','.join(items) + '\n')


def write_fmlp(seqs, path: Path):
    """Write user_id item1 item2 … (space-separated)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        for uid, items in seqs.items():
            f.write(uid + ' ' + ' '.join(items) + '\n')


def copy_file(src: Path, dst: Path):
    import shutil
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


# ── noise injection ───────────────────────────────────────────────────────────

def inject_noise(seqs: dict, ratio: float, seed: int) -> dict:
    """Insert floor(len(seq)*ratio) random items at random positions per user."""
    if ratio == 0.0:
        return {u: list(items) for u, items in seqs.items()}
    rng = random.Random(seed)
    all_items = list({i for items in seqs.values() for i in items})
    noisy = {}
    for u, items in seqs.items():
        n_add = max(1, int(len(items) * ratio))
        extra = rng.choices(all_items, k=n_add)
        combined = list(items)
        for item in extra:
            pos = rng.randint(0, len(combined))
            combined.insert(pos, item)
        noisy[u] = combined
    return noisy


# ── STEAM mode ────────────────────────────────────────────────────────────────

def process_steam(dataset, src_root, dst_root, levels, dry_run):
    src = Path(src_root) / dataset
    if not src.exists():
        print(f"  [skip] {dataset}: not found at {src}")
        return

    train = read_steam_csv(src / "train.dat")
    # test, valid, negatives: copied unchanged (noise is train-only)
    extra_files = ["valid.dat", "test.dat", "valid_neg.dat", "test_neg.dat"]

    total_train = sum(len(v) for v in train.values())
    print(f"  {dataset}: {len(train)} users, {total_train} train interactions")

    for level in levels:
        ratio = NOISE_RATIO[level]
        seed  = NOISE_SEED[level]
        noisy = inject_noise(train, ratio, seed)
        noisy_total = sum(len(v) for v in noisy.values())
        print(f"    {level}: {total_train} -> {noisy_total} train interactions (+{noisy_total-total_train})")

        if dry_run:
            continue

        dst = Path(dst_root) / f"{dataset}_{level}"
        write_steam_csv(noisy, dst / "train.dat")
        for fname in extra_files:
            sp = src / fname
            if sp.exists():
                copy_file(sp, dst / fname)
        print(f"    written -> {dst}")


# ── FMLP mode ─────────────────────────────────────────────────────────────────

def process_fmlp(dataset, src_root, dst_root, levels, dry_run):
    """FMLP uses a single file <Dataset>.txt; noise variants go alongside it."""
    src_file = Path(src_root) / f"{dataset}.txt"
    if not src_file.exists():
        print(f"  [skip] {dataset}: {src_file} not found")
        return

    seqs = read_fmlp(src_file)
    total = sum(len(v) for v in seqs.values())
    print(f"  {dataset}: {len(seqs)} users, {total} train interactions (FMLP)")

    for level in levels:
        ratio = NOISE_RATIO[level]
        seed  = NOISE_SEED[level]
        noisy = inject_noise(seqs, ratio, seed)
        noisy_total = sum(len(v) for v in noisy.values())
        print(f"    {level}: {total} -> {noisy_total} (+{noisy_total-total})")

        if dry_run:
            continue

        # N0 is a copy, N2_20/N3_30 are noise variants;
        # write as <Dataset>_<Level>.txt so --data_name=Beauty_N2_20 picks it up
        dst_file = Path(dst_root) / f"{dataset}_{level}.txt"
        write_fmlp(noisy, dst_file)
        print(f"    written -> {dst_file}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode",     required=True, choices=["steam","fmlp"],
                    help="Data format: 'steam' (comma-sep dat files) or 'fmlp' (space-sep txt)")
    ap.add_argument("--src_root", required=True,
                    help="For steam: dir with Beauty/Sports/Yelp subdirs. "
                         "For fmlp: dir with Beauty.txt etc.")
    ap.add_argument("--dst_root", required=True,
                    help="For steam: output root (writes <Dataset>_<Level>/ subdirs). "
                         "For fmlp: dir where noise .txt files are written (usually same as src).")
    ap.add_argument("--datasets", nargs="+", default=["Beauty","Sports","Yelp"])
    ap.add_argument("--levels",   nargs="+", default=["N0","N2_20","N3_30"],
                    choices=list(NOISE_RATIO))
    ap.add_argument("--dry_run",  action="store_true")
    args = ap.parse_args()

    for ds in args.datasets:
        if args.mode == "steam":
            process_steam(ds, args.src_root, args.dst_root, args.levels, args.dry_run)
        else:
            process_fmlp(ds, args.src_root, args.dst_root, args.levels, args.dry_run)


if __name__ == "__main__":
    main()
