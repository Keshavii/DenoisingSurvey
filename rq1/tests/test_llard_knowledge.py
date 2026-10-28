"""Test of the LLaRD knowledge pipeline with a fake model (no GPU, no download), on a tiny made-up ML-1M.

  cd ~/rq1-kit && python tests/test_llard_knowledge.py [path to LLaRD's system_prompt folder]

Checks: kit item k is the k-th smallest raw movie id; all four stages run and resume cleanly; the output files have the
format LLaRD's loader reads (dicts, user -> list); at most 1 item added, 1 item deleted and 1 user link per user;
invalid model picks are dropped and counted, never guessed; nothing outside the training file reaches the knowledge.
"""
import json
import os
import pickle
import shutil
import sys
import tempfile

import numpy as np
import pandas as pd

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT)
from rq1kit import llard_knowledge as K  # noqa: E402

PROMPTS = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/repos/LLaRD/system_prompt")
if not os.path.isdir(PROMPTS):
    PROMPTS = "/home/claude/shuyao-wang/llard/system_prompt"


def make(root, n_users=25, n_items=20):
    raw = os.path.join(root, "raw")
    os.makedirs(raw)
    raw_ids = np.sort(np.random.default_rng(0).choice(np.arange(1, 200), n_items, replace=False))
    pd.DataFrame({"user_id:token": np.repeat(np.arange(1, 4), n_items), "item_id:token": np.tile(raw_ids, 3),
                  "rating:float": 4.0, "timestamp:float": 1}).to_csv(os.path.join(raw, "ml-1m.inter"), sep="\t", index=False)
    pd.DataFrame({"item_id:token": raw_ids, "movie_title:token_seq": [f"Movie {r}" for r in raw_ids],
                  "release_year:token": 1990, "genre:token_seq": "Drama Comedy"}).to_csv(os.path.join(raw, "ml-1m.item"), sep="\t", index=False)
    data = os.path.join(root, "data")
    os.makedirs(data)
    rng = np.random.default_rng(1)
    rows = []
    for u in range(n_users):
        for i in rng.choice(n_items, 8, replace=False):
            rows.append((u, int(i), 0, -1))
    pd.DataFrame(rows, columns=["user", "item", "noisy", "ts"]).to_csv(os.path.join(data, "train.tsv"), sep="\t", index=False)
    json.dump({"n_users": n_users, "n_items": n_items}, open(os.path.join(data, "meta.json"), "w"))
    return raw, data, raw_ids


def run(stage, raw, data, out, build="N0"):
    K.main(["--stage", stage, "--data", data, "--raw", raw, "--prompts", PROMPTS, "--out", out, "--build", build,
            "--backend", "stub", "--embed", "hash", "--cap", "5"])


def main():
    root = tempfile.mkdtemp(prefix="llard_test_")
    raw, data, raw_ids = make(root)
    out = os.path.join(root, "out")
    rows = K.load_items(raw, 20)
    assert [r["raw_id"] for r in rows] == list(raw_ids) and rows[0]["title"] == f"Movie {raw_ids[0]}"
    print("ok  item k is the k-th smallest raw movie id")
    for st in ("items", "users", "knowledge", "embed"):
        run(st, raw, data, out)
    d = os.path.join(out, "N0")
    tr = np.load(os.path.join(d, "traindata.npy"), allow_pickle=True).tolist()
    aug = np.load(os.path.join(d, "rel_k", "aug_traindata.npy"), allow_pickle=True).tolist()
    uu = np.load(os.path.join(d, "rel_k", "uu_data.npy"), allow_pickle=True).tolist()
    assert isinstance(aug, dict) and set(aug) == set(tr) == set(range(25))
    for u in range(25):
        add, dele = set(aug[u]) - set(tr[u]), set(tr[u]) - set(aug[u])
        assert len(add) <= 1 and len(dele) <= 1 and len(uu[u]) <= 1 and u not in uu[u], (u, add, dele, uu[u])
        assert all(0 <= i < 20 for i in aug[u]) and all(0 <= v < 25 for v in uu[u])
    rep = json.load(open(os.path.join(d, "report_knowledge.json")))
    assert rep["invalid_or_missing"]["user_C"] == 5 and sum(len(v) == 0 for v in uu.values()) == 5, rep  # users 0,5,10,15,20 got an invalid pick
    print("ok  format and counts: <=1 added, <=1 deleted, <=1 user link; invalid picks dropped:", rep["invalid_or_missing"])
    for name, n in (("usr_emb_np.pkl", 25), ("itm_emb_np.pkl", 20)):
        e = pickle.load(open(os.path.join(d, "prf_k", name), "rb"))
        assert e.shape[0] == n and e.dtype == np.float32
    print("ok  embeddings: one row per user and per item")
    shown = json.load(open(os.path.join(d, "shown.json")))
    assert all(len(v) <= 5 for v in shown.values()) and all(set(shown[u]) <= set(tr[int(u)]) for u in shown)
    print("ok  at most --cap history items shown, all from the user's own training history")
    # a second run resumes without error and gives identical files
    before = open(os.path.join(d, "rel_k", "aug_traindata.npy"), "rb").read()
    for st in ("users", "knowledge"):
        run(st, raw, data, out)
    assert before == open(os.path.join(d, "rel_k", "aug_traindata.npy"), "rb").read()
    print("ok  rerun gives identical knowledge")
    shutil.rmtree(root)
    print("ALL LLARD KNOWLEDGE TESTS PASSED")


if __name__ == "__main__":
    main()
