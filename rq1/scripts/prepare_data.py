"""Turn the five RQ1 datasets into the kit's shared format (see rq1kit/data.py).

  python scripts/prepare_data.py --dataset adressa  --src ~/repos/DenoisingRec/data/adressa  --out data/adressa
  python scripts/prepare_data.py --dataset yelp     --src ~/repos/DenoisingRec/data/yelp     --out data/yelp
  python scripts/prepare_data.py --dataset amazon_book --src ~/repos/DenoisingRec/data/amazon_book --out data/amazon_book
  python scripts/prepare_data.py --dataset ml1m     --src ~/repos/RGCF/dataset/ml-1m/ml-1m.inter --out data/ml1m
  python scripts/prepare_data.py --dataset gowalla  --src ~/repos/PLD/data/Gowalla/data.json   --out data/gowalla

Sources and rules
- adressa, yelp, amazon_book: the ADT release (DenoisingRec). Its train/valid/test split is kept as published, so our
  numbers sit next to ADT, DeCA, SGDL and DCF. Column 3 of train/valid is 1 = clean, 0 = noisy (ratings under 3 for
  Yelp and Amazon-Book, dwell time under 10 s for Adressa). Checked: Yelp has 260,581 and Amazon-Book 199,475 flag-0
  train rows, the false-positive counts UDT reports, and every row of DeCA's clean Adressa test file carries flag 1.
  Test = the positive (user, item) on each line of *.test.negative; the 999 sampled negatives in Adressa are ignored
  (we rank all items). No timestamps are shipped.
- ml1m: RecBole's ml-1m.inter (shipped in the RGCF repo, unzip dataset/ml-1m.zip first; identical to GroupLens
  ratings.dat). Rating under 3 = noisy. Per-user chronological 80/10/10; noisy interactions stay in train and in
  valid_noisy, and are removed from valid_clean and test.
- gowalla: PLD's data.json (LightGCN's Gowalla, train and test merged, no timestamps). No natural noise label, so all
  interactions are clean and only injected noise is used. Per-user random 80/10/10 with seed 2026.
"""
import argparse
import ast
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rq1kit.data import chrono_split, reindex, write_split  # noqa: E402


def adt(src, name):
    tr = pd.read_csv(os.path.join(src, f"{name}.train.rating"), sep="\t", header=None, names=["user", "item", "flag"])
    va = pd.read_csv(os.path.join(src, f"{name}.valid.rating"), sep="\t", header=None, names=["user", "item", "flag"])
    rows = []
    with open(os.path.join(src, f"{name}.test.negative")) as f:
        for line in f:
            first = line.rstrip("\n").split("\t")
            if first[0].startswith("("):
                u, i = ast.literal_eval(first[0])
            else:
                u, i = int(first[0]), int(first[1])
            rows.append((u, i))
    te = pd.DataFrame(rows, columns=["user", "item"])
    for d in (tr, va):
        d["noisy"] = (d["flag"] == 0).astype(int)
        d["ts"] = -1
    te["ts"] = -1
    n_users = int(max(tr.user.max(), va.user.max(), te.user.max()) + 1)
    n_items = int(max(tr.item.max(), va.item.max(), te.item.max()) + 1)
    if name == "adressa":  # ADT hard-codes these sizes (data_utils.py:21-23)
        n_users, n_items = max(n_users, 212231), max(n_items, 6596)
    meta = dict(n_users=n_users, n_items=n_items, source=f"DenoisingRec/data/{name}",
                proxy_rule="dwell time under 10 s" if name == "adressa" else "rating under 3",
                split_rule="published ADT split, kept as is")
    return tr, va[va.noisy == 0], va, te, meta


def ml1m(src, seed=2026):
    df = pd.read_csv(src, sep="\t")
    df.columns = [c.split(":")[0] for c in df.columns]
    df = df.rename(columns={"user_id": "user", "item_id": "item", "timestamp": "ts"})
    df["noisy"] = (df["rating"] < 3).astype(int)
    df, nu, ni, _ = reindex(df)
    tr, va, te = chrono_split(df[["user", "item", "noisy", "ts"]], seed=seed)
    meta = dict(n_users=nu, n_items=ni, source="RecBole ml-1m.inter", proxy_rule="rating under 3",
                split_rule="per-user chronological 80/10/10")
    return tr, va[va.noisy == 0], va, te[te.noisy == 0], meta


def gowalla(src, seed=2026):
    d = json.load(open(src))
    rows = [(u, i) for u, items in d.items() for i in items]
    df = pd.DataFrame(rows, columns=["user", "item"]).drop_duplicates()
    df, nu, ni, _ = reindex(df)
    rng = np.random.default_rng(seed)
    df = df.assign(noisy=0, ts=rng.permutation(len(df)))  # random order acts as a random split
    tr, va, te = chrono_split(df, seed=seed)
    tr = tr.assign(ts=-1); va = va.assign(ts=-1); te = te.assign(ts=-1)
    meta = dict(n_users=nu, n_items=ni, source="PLD data/Gowalla/data.json (LightGCN Gowalla)",
                proxy_rule="none (no natural noise label)", split_rule="per-user random 80/10/10, seed 2026")
    return tr, va, va, te, meta


def sanity_yelp2018(src):
    """LightGCN's own Yelp2018 split (shipped in SGL-Torch/dataset/yelp2018). Sanity check ONLY: it has no validation
    set, so validation = test, exactly as the LightGCN paper selects. Never report these numbers in the paper."""
    tr = pd.read_csv(os.path.join(src, "yelp2018.train"), header=None, names=["user", "item"])
    te = pd.read_csv(os.path.join(src, "yelp2018.test"), header=None, names=["user", "item"])
    tr = tr.assign(noisy=0, ts=-1); te = te.assign(noisy=0, ts=-1)
    nu = int(max(tr.user.max(), te.user.max()) + 1); ni = int(max(tr.item.max(), te.item.max()) + 1)
    meta = dict(n_users=nu, n_items=ni, source="SGL-Torch dataset/yelp2018 (LightGCN split)",
                proxy_rule="none", split_rule="LightGCN train/test; validation = test (sanity check only)")
    return tr, te, te, te, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=["adressa", "yelp", "amazon_book", "ml1m", "gowalla", "sanity_yelp2018"])
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.dataset in ("adressa", "yelp", "amazon_book"):
        parts = adt(os.path.expanduser(a.src), a.dataset)
    elif a.dataset == "ml1m":
        parts = ml1m(os.path.expanduser(a.src))
    elif a.dataset == "gowalla":
        parts = gowalla(os.path.expanduser(a.src))
    else:
        parts = sanity_yelp2018(os.path.expanduser(a.src))
    tr, vc, vn, te, meta = parts
    meta["dataset"] = a.dataset
    meta = write_split(a.out, tr, vc, vn, te, meta)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
