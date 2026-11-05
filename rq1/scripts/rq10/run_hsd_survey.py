"""
CLI wrapper for HSD's run_hsd.py (zc-97/HSD @ 9c146a0) — adds --dataset and --sub_model, saves the result as JSON.

Place this file alongside run_hsd.py in the hsd repo root and run from there:
  python run_hsd_survey.py --dataset Beauty --sub_model SASRec

run_hsd.py has no argparse; this wrapper loads it with importlib (its __main__ block does not run) and calls main().
Training and evaluation are the authors' code, unchanged. Only the last step is replaced: the authors'
record_model_result() appends a row to 'denoising-ml.xlsx', and it cannot work at this commit, because main() has
already rebound `dataset` to a RecBole Dataset object, so `dataset += '/' + mode` raises TypeError (seen on PC3,
5 Nov, after training and evaluation had finished). The replacement writes the same numbers (best valid result,
test result, parameters) to results/hsd_<dataset>_<sub_model>.json and prints them.
"""
import argparse
import importlib.util
import json
import os
import time

ap = argparse.ArgumentParser()
ap.add_argument("--dataset", default="Beauty",
                help="Dataset name; must have dataset/<name>/<name>.inter in this dir")
ap.add_argument("--sub_model", default="SASRec",
                help="RecBole backbone: SASRec, BERT4Rec, GRU4Rec, etc.")
args = ap.parse_args()

# Load run_hsd.py without triggering its __main__ block
_here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("_run_hsd_orig", os.path.join(_here, "run_hsd.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _plain(x):
    """RecBole returns OrderedDicts of numpy/torch scalars; make them JSON-safe."""
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    try:
        return float(x)
    except (TypeError, ValueError):
        return str(x)


def record_model_result_json(dataset, model_name, parameter_dict, rst_dic, note, config):
    os.makedirs(os.path.join(_here, "results"), exist_ok=True)
    out = os.path.join(_here, "results", f"hsd_{args.dataset}_{args.sub_model}.json")
    rec = {"dataset": args.dataset, "model": model_name, "sub_model": args.sub_model,
           "finished": time.strftime("%Y-%m-%d %H:%M:%S"), "note": note,
           "parameters": _plain(parameter_dict), **_plain(rst_dic)}
    with open(out, "w") as f:
        json.dump(rec, f, indent=1)
    print("RESULT", json.dumps(rec))
    print("saved", out)


mod.record_model_result = record_model_result_json   # main() looks it up in the module at call time
mod.main("HSD", args.dataset, args.sub_model)
