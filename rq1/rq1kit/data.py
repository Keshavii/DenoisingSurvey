"""Canonical dataset format shared by every RQ1 run.

A prepared dataset is a folder with:
  train.tsv        user  item  noisy  ts     (noisy: 0 clean, 1 natural proxy-noisy, 2 injected; ts = -1 if unknown)
  valid_clean.tsv  user  item  ts          (proxy-noisy interactions removed)
  valid_noisy.tsv  user  item  noisy ts    (everything that fell in the validation window, as collected)
  test.tsv         user  item  ts          (clean positives only)
  meta.json        n_users, n_items, source, proxy rule, split rule

User and item ids are contiguous integers starting at 0, shared by all files.
"""
import json
import os

import numpy as np
import pandas as pd
import scipy.sparse as sp

TRAIN_COLS = ["user", "item", "noisy", "ts"]


def load_split(folder, train_file="train.tsv"):
    meta = json.load(open(os.path.join(folder, "meta.json")))
    train = pd.read_csv(os.path.join(folder, train_file), sep="\t")
    valid_clean = pd.read_csv(os.path.join(folder, "valid_clean.tsv"), sep="\t")
    valid_noisy = pd.read_csv(os.path.join(folder, "valid_noisy.tsv"), sep="\t")
    test = pd.read_csv(os.path.join(folder, "test.tsv"), sep="\t")
    return meta, train, valid_clean, valid_noisy, test


def to_csr(df, n_users, n_items):
    """Binary user x item matrix from a dataframe with user and item columns."""
    d = df.drop_duplicates(["user", "item"])
    data = np.ones(len(d), dtype=np.float32)
    return sp.csr_matrix((data, (d["user"].values, d["item"].values)), shape=(n_users, n_items))


def write_split(folder, train, valid_clean, valid_noisy, test, meta):
    os.makedirs(folder, exist_ok=True)
    train[TRAIN_COLS].to_csv(os.path.join(folder, "train.tsv"), sep="\t", index=False)
    valid_clean[["user", "item", "ts"]].to_csv(os.path.join(folder, "valid_clean.tsv"), sep="\t", index=False)
    valid_noisy[["user", "item", "noisy", "ts"]].to_csv(os.path.join(folder, "valid_noisy.tsv"), sep="\t", index=False)
    test[["user", "item", "ts"]].to_csv(os.path.join(folder, "test.tsv"), sep="\t", index=False)
    meta = dict(meta)
    meta.update(
        n_train=int(len(train)),
        n_train_noisy=int((train["noisy"] > 0).sum()),
        n_valid_clean=int(len(valid_clean)),
        n_valid_noisy=int(len(valid_noisy)),
        n_test=int(len(test)),
        natural_noise_share=float((train["noisy"] == 1).mean()) if len(train) else 0.0,
        density=float(len(train) + len(valid_noisy) + len(test)) / (meta["n_users"] * meta["n_items"]),
    )
    json.dump(meta, open(os.path.join(folder, "meta.json"), "w"), indent=2)
    return meta


def chrono_split(df, ratios=(0.8, 0.1, 0.1), seed=0):
    """Per-user chronological split. Users with fewer than 3 interactions keep everything in train.

    df needs columns user, item, noisy, ts. Ties in ts are broken randomly with a fixed seed.
    Returns train, valid (all), test (all) dataframes before clean filtering.
    """
    rng = np.random.default_rng(seed)
    df = df.assign(_r=rng.random(len(df))).sort_values(["user", "ts", "_r"])
    parts = {"train": [], "valid": [], "test": []}
    for _, g in df.groupby("user", sort=False):
        n = len(g)
        if n < 3:
            parts["train"].append(g)
            continue
        n_test = max(1, int(round(n * ratios[2])))
        n_valid = max(1, int(round(n * ratios[1])))
        n_train = n - n_valid - n_test
        if n_train < 1:
            n_train, n_valid, n_test = n - 2, 1, 1
        parts["train"].append(g.iloc[:n_train])
        parts["valid"].append(g.iloc[n_train:n_train + n_valid])
        parts["test"].append(g.iloc[n_train + n_valid:])
    out = [pd.concat(parts[k]).drop(columns="_r") if parts[k] else df.iloc[:0].drop(columns="_r") for k in ("train", "valid", "test")]
    return out


def reindex(df):
    """Map raw user/item ids to 0..n-1. Returns df, n_users, n_items, maps."""
    u_codes, u_uni = pd.factorize(df["user"], sort=True)
    i_codes, i_uni = pd.factorize(df["item"], sort=True)
    df = df.assign(user=u_codes, item=i_codes)
    return df, len(u_uni), len(i_uni), (u_uni, i_uni)
