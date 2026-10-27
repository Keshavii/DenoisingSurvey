"""MostPop reference: rank items by training popularity (CPU only)."""
import argparse, json, os, sys
import numpy as np, torch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rq1kit.data import load_split
from rq1kit.evaluate import evaluate
from rq1kit.export import export_topk
ap = argparse.ArgumentParser(); ap.add_argument("--data", required=True); ap.add_argument("--train_file", default="train.tsv")
a = ap.parse_args()
meta, train, *_ = load_split(a.data, a.train_file)
score = torch.tensor(np.bincount(train["item"].values, minlength=meta["n_items"]).astype(np.float32))
ds = os.path.basename(os.path.normpath(a.data)); tag = a.train_file.replace(".tsv", ""); rd = f"runs/{ds}/mostpop_{tag}"
export_topk(lambda u: score.unsqueeze(0).expand(len(u), -1), a.data, rd, a.train_file, device="cpu")
out = {"dataset": ds, "train_file": a.train_file, "method": "MostPop"}
for split, f in (("valid_clean", "topk_valid.npy"), ("test", "topk_test.npy")):
    r = evaluate(a.data, os.path.join(rd, f), split, a.train_file)
    out[split] = {k: r[k] for k in ("recall@20", "ndcg@20", "seen_item_leak_rate")}
os.makedirs("results/mostpop", exist_ok=True)
json.dump(out, open(f"results/mostpop/{ds}_{tag}.json", "w"), indent=2)
print(f"{ds:12s} {tag:20s} valid_clean NDCG@20 {out['valid_clean']['ndcg@20']:.4f}  test NDCG@20 {out['test']['ndcg@20']:.4f}  test Recall@20 {out['test']['recall@20']:.4f}")
