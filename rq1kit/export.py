"""Helper every adapter calls at the end of training to write top-K files the evaluator reads.

Inside an official repo, after the best model (chosen on VALIDATION) is restored:

    import sys; sys.path.insert(0, "/path/to/rq1-kit")
    from rq1kit.export import export_topk
    export_topk(score_fn, data_dir="/path/to/data/yelp", out_dir=run_dir, train_file="train.tsv")

score_fn(user_ids: LongTensor[B]) -> FloatTensor[B, n_items] must return the model's scores for all items
(higher = better), in the canonical item ids. Two files are written:
    topk_valid.npy  training items masked                 (used for model selection checks and RQ2)
    topk_test.npy   training and validation items masked  (the reported result)
"""
import os

import numpy as np

from .data import load_split, to_csr


def export_topk(score_fn, data_dir, out_dir, train_file="train.tsv", k=100, batch=1024, device=None):
    import torch

    meta, train, valid_clean, valid_noisy, test = load_split(data_dir, train_file)
    nu, ni = meta["n_users"], meta["n_items"]
    train_csr = to_csr(train, nu, ni)
    valid_csr = to_csr(valid_noisy, nu, ni)
    if "validation = test" in meta.get("split_rule", ""):  # sanity split: do not hide the test items themselves
        valid_csr = __import__("scipy.sparse", fromlist=["csr_matrix"]).csr_matrix((nu, ni), dtype=valid_csr.dtype)
    os.makedirs(out_dir, exist_ok=True)
    out = {"valid": np.full((nu, k), -1, dtype=np.int64), "test": np.full((nu, k), -1, dtype=np.int64)}
    with torch.no_grad():
        for start in range(0, nu, batch):
            users = torch.arange(start, min(start + batch, nu))
            if device is not None:
                users = users.to(device)
            scores = score_fn(users).float()
            dev = scores.device
            rows = slice(start, start + len(users))
            tr = torch.tensor(train_csr[rows].toarray(), device=dev, dtype=torch.bool)
            va = torch.tensor(valid_csr[rows].toarray(), device=dev, dtype=torch.bool)
            s_valid = scores.masked_fill(tr, float("-inf"))
            s_test = s_valid.masked_fill(va, float("-inf"))
            for name, s in (("valid", s_valid), ("test", s_test)):
                vals, idx = torch.topk(s, k=min(k, ni), dim=1)
                idx[torch.isinf(vals)] = -1
                out[name][rows, :idx.shape[1]] = idx.cpu().numpy()
    for name, arr in out.items():
        np.save(os.path.join(out_dir, f"topk_{name}.npy"), arr)
    return {n: os.path.join(out_dir, f"topk_{n}.npy") for n in out}
