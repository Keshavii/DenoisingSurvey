"""
CLI wrapper for run_hsd.py — adds --dataset and --sub_model arguments.

Place this file alongside run_hsd.py in the hsd repo root and run from there:
  python run_hsd_survey.py --dataset Beauty --sub_model SASRec

The original run_hsd.py has no argparse; this wrapper imports its main()
using importlib so the __main__ guard fires for the wrapper, not the original.
"""
import argparse
import importlib.util
import os
import sys

ap = argparse.ArgumentParser()
ap.add_argument("--dataset",   default="Beauty",
                help="Dataset name; must have dataset/<name>/<name>.inter in this dir")
ap.add_argument("--sub_model", default="SASRec",
                help="RecBole backbone: SASRec, BERT4Rec, GRU4Rec, etc.")
args = ap.parse_args()

# Load run_hsd.py without triggering its __main__ block
_here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("_run_hsd_orig",
                                               os.path.join(_here, "run_hsd.py"))
mod = importlib.util.module_from_spec(spec)
# __name__ will be '_run_hsd_orig', so the if __name__ == '__main__': block is skipped
spec.loader.exec_module(mod)

mod.main("HSD", args.dataset, args.sub_model)
