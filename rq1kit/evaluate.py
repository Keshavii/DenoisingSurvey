"""One evaluator for every method.

Every adapter exports a top-K file for all users: a .npy int array of shape [n_users, K] (K >= 50),
items ranked best first, with the user's training items (and, for the test file, validation items)
already removed, padded with -1. The evaluator re-checks the masking and refuses lists that leak.

Usage:
  python -m rq1kit.evaluate --data data/yelp --topk runs/yelp/tce_lightgcn_N0_s1/topk_test.npy \
      --split test --out results/yelp__tce__lightgcn__N0__s1.json --tag method=T-CE backbone=LightGCN cond=N0 seed=1
"""
import argparse
import json
import os
import time

import numpy as np

from .data import load_split, to_csr

KS = (10, 20, 50)


def _per_user_metrics(topk, truth_csr, ks=KS):
    """Recall@K and NDCG@K for every user with at least one truth item. Returns dict of arrays and the user ids."""
    users = np.where(np.diff(truth_csr.indptr) > 0)[0]
    out = {f"recall@{k}": np.zeros(len(users)) for k in ks}
    out.update({f"ndcg@{k}": np.zeros(len(users)) for k in ks})
    discounts = 1.0 / np.log2(np.arange(2, max(ks) + 2))
    for row, u in enumerate(users):
        truth = truth_csr.indices[truth_csr.indptr[u]:truth_csr.indptr[u + 1]]
        lst = topk[u, :max(ks)]
        hit = np.isin(lst, truth)
        for k in ks:
            h = hit[:k]
            out[f"recall@{k}"][row] = h.sum() / len(truth)
            idcg = discounts[:min(len(truth), k)].sum()
            out[f"ndcg@{k}"][row] = (h * discounts[:k]).sum() / idcg
    return users, out


def check_leakage(topk, seen_csr, sample=2000, seed=0):
    """Fraction of sampled users whose list contains an item they already interacted with in training/validation."""
    rng = np.random.default_rng(seed)
    users = rng.choice(topk.shape[0], size=min(sample, topk.shape[0]), replace=False)
    bad = 0
    for u in users:
        seen = seen_csr.indices[seen_csr.indptr[u]:seen_csr.indptr[u + 1]]
        if np.isin(topk[u], seen).any():
            bad += 1
    return bad / len(users)


def group_breakdown(users, per_user, train_csr, truth_csr, topk):
    """Metrics by user history group and by item popularity tertile (RQ8 re-uses these)."""
    hist = np.diff(train_csr.indptr)[users]
    groups = {
        "cold(<5)": hist < 5,
        "warm(5-20)": (hist >= 5) & (hist <= 20),
        "established(>20)": hist > 20,
    }
    q = np.quantile(hist, [0.2, 0.4, 0.6, 0.8])
    qid = np.searchsorted(q, hist, side="right")
    for i in range(5):
        groups[f"user_q{i + 1}"] = qid == i
    res = {}
    for g, m in groups.items():
        if m.sum() == 0:
            continue
        res[g] = {"n_users": int(m.sum()), "ndcg@20": float(per_user["ndcg@20"][m].mean()),
                  "recall@20": float(per_user["recall@20"][m].mean())}
    # item popularity tertiles: recall@20 restricted to truth items in each tertile
    pop = np.asarray(train_csr.sum(0)).ravel()
    pos = pop[pop > 0]
    cut = np.quantile(pos, [1 / 3, 2 / 3]) if len(pos) else [0, 0]
    tert = np.where(pop <= cut[0], 0, np.where(pop <= cut[1], 1, 2))  # 0 tail, 1 mid, 2 head
    for t, name in ((2, "items_head"), (1, "items_mid"), (0, "items_tail")):
        hits, tot = 0, 0
        for u in users:
            truth = truth_csr.indices[truth_csr.indptr[u]:truth_csr.indptr[u + 1]]
            truth = truth[tert[truth] == t]
            if len(truth) == 0:
                continue
            tot += len(truth)
            hits += np.isin(topk[u, :20], truth).sum()
        if tot:
            res[name] = {"n_truth": int(tot), "recall@20_micro": float(hits / tot)}
    # beyond accuracy
    top20 = topk[:, :20]
    valid = top20[top20 >= 0]
    counts = np.bincount(valid, minlength=train_csr.shape[1]).astype(float)
    res["coverage@20"] = float((counts > 0).mean())
    srt = np.sort(counts)
    n = len(srt)
    res["gini@20"] = float((2 * np.arange(1, n + 1) - n - 1).dot(srt) / (n * srt.sum())) if srt.sum() else 0.0
    return res


def evaluate(data_dir, topk_path, split="test", train_file="train.tsv"):
    meta, train, valid_clean, valid_noisy, test = load_split(data_dir, train_file)
    nu, ni = meta["n_users"], meta["n_items"]
    topk = np.load(topk_path)
    assert topk.shape[0] == nu, f"top-K has {topk.shape[0]} rows, dataset has {nu} users"
    assert topk.shape[1] >= max(KS), f"need at least {max(KS)} items per user"
    train_csr = to_csr(train[train["noisy"] >= 0], nu, ni)
    if split == "test":
        truth = test
        seen = to_csr(__import__("pandas").concat([train[["user", "item"]], valid_noisy[["user", "item"]]]), nu, ni)
        if "validation = test" in meta.get("split_rule", ""):  # sanity split: validation is the test set
            seen = train_csr
    elif split == "valid_clean":
        truth, seen = valid_clean, train_csr
    elif split == "valid_noisy":
        truth, seen = valid_noisy, train_csr
    else:
        raise ValueError(split)
    truth_csr = to_csr(truth, nu, ni)
    leak = check_leakage(topk, seen)
    users, per_user = _per_user_metrics(topk, truth_csr)
    res = {k: float(v.mean()) for k, v in per_user.items()}
    res["n_eval_users"] = int(len(users))
    res["seen_item_leak_rate"] = leak
    if split == "test":
        res["groups"] = group_breakdown(users, per_user, train_csr, truth_csr, topk)
    np.save(topk_path.replace(".npy", f"_{split}_peruser_ndcg20.npy"), np.stack([users, per_user["ndcg@20"]]))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--topk", required=True)
    ap.add_argument("--split", default="test", choices=["test", "valid_clean", "valid_noisy"])
    ap.add_argument("--train_file", default="train.tsv")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", nargs="*", default=[], help="key=value pairs stored with the result")
    a = ap.parse_args()
    res = evaluate(a.data, a.topk, a.split, a.train_file)
    if res["seen_item_leak_rate"] > 0:
        print(f"WARNING: {res['seen_item_leak_rate']:.1%} of sampled users have already-seen items in their list; "
              "fix the adapter's masking before trusting this number")
    res.update(dict(t.split("=", 1) for t in a.tag))
    res.update(data=a.data, topk=a.topk, split=a.split, evaluated_at=time.strftime("%Y-%m-%d %H:%M:%S"))
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=2)
    print(json.dumps({k: v for k, v in res.items() if k != "groups"}, indent=2))


if __name__ == "__main__":
    main()
