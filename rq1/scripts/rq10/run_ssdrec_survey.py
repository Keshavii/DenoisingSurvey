"""
CLI wrapper for run_SSDRec.py — adds --dataset and --sub_model arguments.

Place this file alongside run_SSDRec.py in the ssdrec repo root:
  python run_ssdrec_survey.py --dataset Beauty --sub_model SASRec

SSDRec uses the HSD model class plus graph_data augmentation.
The original __main__ block calls main('HSD', ['ml-10k'], 'SASRec');
we keep model_name='HSD' as the original does.
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

# Load run_SSDRec.py without triggering its __main__ block
_here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("_run_ssdrec_orig",
                                               os.path.join(_here, "run_SSDRec.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)   # __name__ = '_run_ssdrec_orig' → __main__ block skipped

# Original __main__ passes model_name='HSD' even for SSDRec; keep that convention
mod.main("HSD", args.dataset, args.sub_model)
