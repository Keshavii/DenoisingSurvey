"""
RQ10 common evaluator.

Loads each specialist's saved checkpoint and re-evaluates using
full-ranking Recall@20 and NDCG@20 on our shared test split.
One script; six method adapters (GBSR, HDSR, GDMSR, STEAM, FMLP, PreferDiff).
HSD and SSDRec use RecBole's own evaluator (full-ranking mode) since their
checkpoints are saved by RecBole itself.

Usage:
  python rq10_eval.py --method gbsr \
      --ckpt ~/survey/rq10/repos/gbsr/torch_version/saved/best.pth \
      --data ~/survey/rq10/data/douban_book_N0 \
      --out  ~/survey/rq10/results/gbsr_douban_N0.tsv

  # Batch mode: evaluate all done runs in results/ against run_summary.tsv
  python rq10_eval.py --batch ~/survey/rq10 --out ~/survey/rq10/results/common_eval.tsv

Output TSV: method  dataset  noise_level  recall@20  ndcg@20  checkpoint
"""
import argparse, importlib, os, sys, json
from pathlib import Path
import numpy as np

K = 20  # top-K for all metrics


# ─────────────────────────────────────────────────────────────────────────────
# Metric helpers (pure numpy, no torch)
# ─────────────────────────────────────────────────────────────────────────────

def recall_at_k(ranked: np.ndarray, pos_set: set, k: int) -> float:
    hits = sum(1 for i in ranked[:k] if i in pos_set)
    return hits / len(pos_set)


def ndcg_at_k(ranked: np.ndarray, pos_set: set, k: int) -> float:
    dcg = sum(1.0 / np.log2(i + 2) for i, item in enumerate(ranked[:k]) if item in pos_set)
    idcg = sum(1.0 / np.log2(i + 2) for i in range(min(len(pos_set), k)))
    return dcg / idcg if idcg > 0 else 0.0


def evaluate_rankings(user_rankings: dict, user_positives: dict):
    """
    user_rankings:  dict[user_id -> list of item_ids, sorted best-first]
    user_positives: dict[user_id -> set of held-out item_ids]
    Returns: mean recall@K, mean ndcg@K
    """
    recalls, ndcgs = [], []
    for u, ranked in user_rankings.items():
        pos = user_positives.get(u)
        if not pos:
            continue
        ranked_arr = np.array(ranked)
        recalls.append(recall_at_k(ranked_arr, pos, K))
        ndcgs.append(ndcg_at_k(ranked_arr, pos, K))
    return float(np.mean(recalls)), float(np.mean(ndcgs))


# ─────────────────────────────────────────────────────────────────────────────
# Data loaders (STEAM pair/seq format → {user: [train items], test: {item}})
# ─────────────────────────────────────────────────────────────────────────────

def load_steam_data(data_dir: Path):
    """
    Returns:
      train_seqs:   dict[user -> list[item]]  (all training items)
      test_pos:     dict[user -> set[item]]   (held-out test items)
      all_items:    set of all item ids seen in training
    """
    def _read(path, fmt):
        d = {}
        if not path.exists():
            return d
        with open(path) as f:
            for ln in f:
                parts = ln.strip().split()
                if not parts:
                    continue
                if fmt == "pair":
                    d.setdefault(parts[0], []).append(parts[1])
                else:  # seq: user i1 i2 ...
                    d[parts[0]] = parts[1:]
        return d

    td = data_dir / "train.dat"
    if not td.exists():
        raise FileNotFoundError(f"train.dat not found in {data_dir}")
    with open(td) as f:
        first = f.readline().split()
    fmt = "pair" if len(first) == 2 else "seq"

    train  = _read(data_dir / "train.dat",  fmt)
    test   = _read(data_dir / "test.dat",   fmt)
    all_items = {i for seqs in train.values() for i in seqs}
    test_pos  = {u: set(items) for u, items in test.items() if items}
    return train, test_pos, all_items


# ─────────────────────────────────────────────────────────────────────────────
# Method adapters
# Each adapter: load_model(ckpt, data_dir, env_bin) -> callable(user_id, train_items, all_items) -> ranked_list
# ─────────────────────────────────────────────────────────────────────────────

class STEAMAdapter:
    """
    STEAM saves a model in ./save_model/ (default -o arg).
    Re-evaluate by running test mode with the saved checkpoint, then parse output.
    Fallback: use STEAM's own test-mode output if the checkpoint path is a log file.
    """
    name = "steam"

    def run_eval(self, ckpt_path: Path, data_dir: Path, env_bin: Path, out_tsv: Path):
        """Run STEAM's own test mode and parse Recall/NDCG from stdout."""
        import subprocess
        td = data_dir
        cmd = [
            str(env_bin / "python"), "main.py",
            f"-tf", str(td / "train.dat"),
            f"-vf", str(td / "valid.dat"),
            f"-ef", str(td / "test.dat"),
            f"-vn", str(td / "valid_neg.dat"),
            f"-en", str(td / "test_neg.dat"),
            f"-o",  str(ckpt_path.parent) + "/",
            f"-m",  "test",
        ]
        repo = ckpt_path.parent.parent  # assumes ckpt in <repo>/save_model/
        result = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True,
                                env={**os.environ, "PATH": str(env_bin) + ":" + os.environ["PATH"]})
        # Parse "Recall@20: X  NDCG@20: Y" from stdout
        recall, ndcg = None, None
        for line in result.stdout.splitlines():
            if "Recall@20" in line or "recall@20" in line.lower():
                try:
                    recall = float(line.split(":")[-1].strip().split()[0])
                except Exception:
                    pass
            if "NDCG@20" in line or "ndcg@20" in line.lower():
                try:
                    ndcg = float(line.split(":")[-1].strip().split()[0])
                except Exception:
                    pass
        return recall, ndcg


class GBSRAdapter:
    """
    GBSR (torch port) saves best checkpoint in a run-specific directory.
    Load the model and score all items for each user.
    """
    name = "gbsr"

    def run_eval(self, ckpt_path: Path, data_dir: Path, env_bin: Path, out_tsv: Path):
        # GBSR uses the method's own test pipeline; re-run test mode
        # (the method selects best epoch during training; test results are in the log)
        # For now: parse the log file for test Recall@20 / NDCG@20
        log = ckpt_path.with_suffix(".log")
        if not log.exists():
            log = ckpt_path.parent / "test_result.txt"
        recall, ndcg = None, None
        if log.exists():
            with open(log) as f:
                for line in f:
                    if "recall@20" in line.lower():
                        try:
                            recall = float(line.split("|")[2].strip())
                        except Exception:
                            pass
                    if "ndcg@20" in line.lower():
                        try:
                            ndcg = float(line.split("|")[2].strip())
                        except Exception:
                            pass
        return recall, ndcg


# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────

ADAPTERS = {
    "steam":      STEAMAdapter,
    "gbsr":       GBSRAdapter,
    # hdsr, gdmsr, fmlp, preferdiff: added in next session once checkpoint paths confirmed
}


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method",  help="Method name (gbsr, steam, hdsr, …)")
    ap.add_argument("--ckpt",    help="Path to saved checkpoint")
    ap.add_argument("--data",    help="Data directory (STEAM format)")
    ap.add_argument("--env_bin", help="Conda env bin dir for the method")
    ap.add_argument("--out",     help="Output .tsv path")
    ap.add_argument("--batch",   help="Root dir; evaluate all entries in run_summary.tsv")
    return ap.parse_args()


def main():
    args = parse_args()

    if args.batch:
        root = Path(args.batch)
        summary = root / "results" / "run_summary.tsv"
        if not summary.exists():
            print(f"No run_summary.tsv at {summary}"); return
        out = Path(args.out) if args.out else root / "results" / "common_eval.tsv"
        with open(summary) as f, open(out, "w") as fo:
            fo.write("method\tdataset\tnoise_level\trecall@20\tndcg@20\tnotes\n")
            for line in f:
                parts = line.strip().split("\t")
                if not parts or parts[0].startswith("#"):
                    continue
                name, rc = parts[0], parts[1] if len(parts) > 1 else "?"
                if rc != "0":
                    fo.write(f"{name}\t-\t-\tFAILED\tFAILED\texit={rc}\n")
                    continue
                # name format: <method>_<dataset>[_<run>]
                # e.g. gbsr_douban_r1, steam_beauty, fmlp_sports
                tokens = name.split("_")
                method = tokens[0]
                dataset = tokens[1] if len(tokens) > 1 else "?"
                note = "_".join(tokens[2:]) if len(tokens) > 2 else ""
                fo.write(f"{method}\t{dataset}\t{note}\tTODO\tTODO\t{name}\n")
        print(f"Skeleton written to {out}")
        print("NOTE: per-method checkpoint loading not yet implemented for all methods.")
        print("      Complete the adapters in ADAPTERS dict or run each method's own test mode.")
        return

    if not args.method or not args.ckpt or not args.data:
        print("Provide --method, --ckpt, --data  or  --batch <root>"); return

    cls = ADAPTERS.get(args.method)
    if cls is None:
        print(f"No adapter for {args.method}. Available: {list(ADAPTERS)}")
        return

    adapter = cls()
    env_bin = Path(args.env_bin) if args.env_bin else Path(
        os.path.expanduser(f"~/miniconda3/envs/r10-{args.method}/bin"))
    out = Path(args.out) if args.out else Path(f"/tmp/eval_{args.method}.tsv")

    recall, ndcg = adapter.run_eval(Path(args.ckpt), Path(args.data), env_bin, out)
    print(f"method={args.method}  recall@{K}={recall}  ndcg@{K}={ndcg}")
    with open(out, "w") as f:
        f.write("method\trecall@20\tndcg@20\n")
        f.write(f"{args.method}\t{recall}\t{ndcg}\n")
    print(f"Written: {out}")


if __name__ == "__main__":
    main()
