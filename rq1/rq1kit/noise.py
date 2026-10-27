"""Noise conditions used across the RQs.

N0  natural: the prepared train.tsv as is (noisy=1 rows are the natural proxy-noisy ones)
clean      : train.tsv without noisy=1 rows (the oracle's training data and the base for N1-N4)
N1  random false positives: unobserved items drawn uniformly
N2  popularity false positives: unobserved items drawn with probability proportional to training degree
N3  hard false positives: unobserved items from ranks 21-100 of an MF model trained on the clean base
    (pass that model's exported top-K file with --mf_topk)
N4  false negatives: hide a share of clean training positives (written to hidden_fn.tsv for scoring)

Rate rho is per user: each user receives rho x (its clean training positives) injected items, with
stochastic rounding so that users with 1-3 interactions (Adressa) still get noise at the right overall rate.
Injected rows get noisy=2 so detection can be scored later. Files are written next to train.tsv:
    train_<COND>_<rate>_s<seed>.tsv   e.g. train_N2_20_s1.tsv
"""
import argparse
import os

import numpy as np
import pandas as pd

from .data import load_split


def _n_per_user(counts, rho, rng):
    base = counts * rho
    n = np.floor(base).astype(int)
    n += (rng.random(len(base)) < (base - n)).astype(int)
    return n


def inject(data_dir, cond, rho, seed, mf_topk=None, base="clean"):
    meta, train, valid_clean, valid_noisy, test = load_split(data_dir)
    rng = np.random.default_rng(seed)
    nu, ni = meta["n_users"], meta["n_items"]
    clean = train[train["noisy"] == 0].copy() if base == "clean" else train.copy()
    if cond == "clean":
        return clean, None
    # everything the user has touched anywhere is never sampled as noise
    touched = pd.concat([train[["user", "item"]], valid_noisy[["user", "item"]], test[["user", "item"]]])
    touched_sets = touched.groupby("user")["item"].apply(set).to_dict()
    counts = clean.groupby("user").size().reindex(range(nu), fill_value=0).values
    if cond == "N4":
        hide = rng.random(len(clean)) < rho
        hidden = clean[hide].assign(noisy=3)
        return clean[~hide], hidden
    n_add = _n_per_user(counts, rho, rng)
    pop = np.bincount(clean["item"].values, minlength=ni).astype(float)
    if cond == "N2":
        p = pop / pop.sum()
    elif cond == "N1":
        p = np.full(ni, 1.0 / ni)
    elif cond == "N3":
        assert mf_topk, "N3 needs --mf_topk (top-K file of an MF-BPR model trained on the clean base)"
        cand = np.load(mf_topk)[:, 20:100]
    else:
        raise ValueError(cond)
    rows = []
    for u in np.nonzero(n_add)[0]:
        seen = touched_sets.get(u, set())
        k = n_add[u]
        if cond == "N3":
            pool = [i for i in cand[u] if i >= 0 and i not in seen]
            pick = rng.choice(pool, size=min(k, len(pool)), replace=False) if pool else []
        else:
            pick, tries = set(), 0
            while len(pick) < k and tries < 50:
                draw = rng.choice(ni, size=2 * k, p=p)
                pick.update(int(i) for i in draw if i not in seen)
                tries += 1
            pick = list(pick)[:k]
        rows += [(u, int(i)) for i in pick]
    added = pd.DataFrame(rows, columns=["user", "item"]).assign(noisy=2, ts=-1)
    noisy_train = pd.concat([clean, added], ignore_index=True)
    return noisy_train, added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--cond", required=True, choices=["clean", "N1", "N2", "N3", "N4"])
    ap.add_argument("--rate", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--mf_topk")
    a = ap.parse_args()
    out, extra = inject(a.data, a.cond, a.rate, a.seed, a.mf_topk)
    tag = "clean" if a.cond == "clean" else f"{a.cond}_{int(round(a.rate * 100))}_s{a.seed}"
    path = os.path.join(a.data, f"train_{tag}.tsv")
    out[["user", "item", "noisy", "ts"]].to_csv(path, sep="\t", index=False)
    if a.cond == "N4" and extra is not None:
        extra.to_csv(os.path.join(a.data, f"hidden_fn_{tag}.tsv"), sep="\t", index=False)
    print(f"wrote {path}: {len(out)} rows, injected/hidden {0 if extra is None else len(extra)}")


if __name__ == "__main__":
    main()
