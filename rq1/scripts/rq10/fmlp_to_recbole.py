"""
Convert FMLP or STEAM sequential data to RecBole .inter format for HSD / SSDRec.

RecBole with eval_args: split: {'LS': 'valid_and_test'} does its own leave-one-out
splitting from a single interaction file, using timestamp as the ordering signal.
We write position-in-sequence as the timestamp (1, 2, 3, ...).

FMLP mode  — input: <src_root>/<Dataset>.txt
             format: user_id item1 item2 … (space-sep, one line per user)

STEAM mode — input: <src_root>/<Dataset>/train.dat + valid.dat + test.dat
             format: item1,item2,… (comma-sep, implicit user = line index)
             We reconstruct the full sequence: train items → valid item → test item
             so RecBole's LS split reproduces the same held-out positions.

Output: <dst_root>/<Dataset>/<Dataset>.inter
        TSV header: user_id:token\\titem_id:token\\ttimestamp:float

Usage:
  # from FMLP data (Beauty.txt confirmed; Sports/Yelp if present)
  python fmlp_to_recbole.py --mode fmlp \\
      --src_root ~/survey/rq10/repos/fmlp/data \\
      --dst_root ~/survey/rq10/repos/hsd/dataset \\
      --datasets Beauty Sports Yelp

  # from STEAM data (Beauty/Sports/Yelp)
  python fmlp_to_recbole.py --mode steam \\
      --src_root ~/survey/rq10/repos/steam \\
      --dst_root ~/survey/rq10/repos/hsd/dataset \\
      --datasets Beauty Sports Yelp
"""
import argparse
from pathlib import Path


def convert_fmlp(src_file: Path, dst_dir: Path, dataset: str, dry_run: bool):
    """FMLP .txt → RecBole .inter  (user_id is explicit in col 0)."""
    out = dst_dir / f"{dataset}.inter"
    n = 0
    if not dry_run:
        dst_dir.mkdir(parents=True, exist_ok=True)
        fout = open(out, 'w')
        fout.write("user_id:token\titem_id:token\ttimestamp:float\n")
    with open(src_file) as fin:
        for line in fin:
            parts = line.strip().split()
            if len(parts) < 2:
                continue
            uid = parts[0]
            for t, item in enumerate(parts[1:], 1):
                if not dry_run:
                    fout.write(f"{uid}\t{item}\t{float(t)}\n")
                n += 1
    if not dry_run:
        fout.close()
    print(f"  {dataset} (fmlp): {n} interactions → {out}")


def convert_steam(src_dir: Path, dst_dir: Path, dataset: str, dry_run: bool):
    """
    STEAM .dat → RecBole .inter  (user = line index, 1-based).
    Combines train + valid + test to give RecBole the full sequence.
    """
    def read_lines(path):
        rows = []
        if not path.exists():
            return rows
        with open(path) as f:
            for idx, ln in enumerate(f, 1):
                items = [x.strip() for x in ln.strip().split(',') if x.strip()]
                rows.append((str(idx), items))
        return rows

    train_rows = read_lines(src_dir / "train.dat")
    valid_rows = read_lines(src_dir / "valid.dat")
    test_rows  = read_lines(src_dir / "test.dat")

    if not train_rows:
        print(f"  [skip] {dataset}: train.dat not found in {src_dir}")
        return

    out = dst_dir / f"{dataset}.inter"
    n = 0
    if not dry_run:
        dst_dir.mkdir(parents=True, exist_ok=True)
        fout = open(out, 'w')
        fout.write("user_id:token\titem_id:token\ttimestamp:float\n")

    for uid, train_items in train_rows:
        full_seq = list(train_items)
        idx = int(uid) - 1          # 0-based row index
        if idx < len(valid_rows):
            full_seq.extend(valid_rows[idx][1])
        if idx < len(test_rows):
            full_seq.extend(test_rows[idx][1])
        for t, item in enumerate(full_seq, 1):
            if not dry_run:
                fout.write(f"{uid}\t{item}\t{float(t)}\n")
            n += 1

    if not dry_run:
        fout.close()
    print(f"  {dataset} (steam): {n} interactions → {out}")


def main():
    ap = argparse.ArgumentParser(
        description="Convert FMLP or STEAM sequential data to RecBole .inter format")
    ap.add_argument("--mode",      required=True, choices=["fmlp", "steam"])
    ap.add_argument("--src_root",  required=True,
                    help="For fmlp: dir with Beauty.txt etc. "
                         "For steam: dir with Beauty/Sports/Yelp subdirs.")
    ap.add_argument("--dst_root",  required=True,
                    help="RecBole dataset root; writes <Dataset>/<Dataset>.inter")
    ap.add_argument("--datasets",  nargs="+", default=["Beauty", "Sports", "Yelp"])
    ap.add_argument("--dry_run",   action="store_true")
    args = ap.parse_args()

    src = Path(args.src_root)
    dst = Path(args.dst_root)

    for ds in args.datasets:
        dst_dir = dst / ds
        if args.mode == "fmlp":
            src_file = src / f"{ds}.txt"
            if not src_file.exists():
                print(f"  [skip] {ds}: {src_file} not found")
                continue
            convert_fmlp(src_file, dst_dir, ds, args.dry_run)
        else:
            src_dir = src / ds
            if not src_dir.exists():
                print(f"  [skip] {ds}: {src_dir} not found")
                continue
            convert_steam(src_dir, dst_dir, ds, args.dry_run)


if __name__ == "__main__":
    main()
