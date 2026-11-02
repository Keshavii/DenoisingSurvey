"""Shared helper for methods whose model scores all items of a user at once (DiffRec, DDRM, ...): clean/noisy validation
NDCG@20 from a score function, same ranking rule as rq1kit.backbone.valid_ndcg (training items masked, NDCG@20 over
users that have validation items)."""
import torch


@torch.no_grad()
def valid_ndcg_scores(score_fn, n_users, train_csr, truth_csrs, device, batch=1024, k=20):
    disc = 1.0 / torch.log2(torch.arange(2, k + 2, device=device).float())
    res = {name: [] for name in truth_csrs}
    for s in range(0, n_users, batch):
        rows = slice(s, min(s + batch, n_users))
        users = torch.arange(rows.start, rows.stop, device=device)
        scores = score_fn(users).float()
        mask = torch.tensor(train_csr[rows].toarray(), device=device, dtype=torch.bool)
        top = torch.topk(scores.masked_fill(mask, float("-inf")), k, dim=1).indices
        for name, tc in truth_csrs.items():
            t = torch.tensor(tc[rows].toarray(), device=device, dtype=torch.bool)
            n_true = t.sum(1)
            keep = n_true > 0
            if keep.sum() == 0:
                continue
            hit = torch.gather(t, 1, top).float()
            dcg = (hit * disc).sum(1)
            idcg = torch.cumsum(disc, 0)[torch.clamp(n_true, max=k) - 1]
            res[name].append((dcg[keep] / idcg[keep]).cpu())
    return {n: float(torch.cat(v).mean()) if v else 0.0 for n, v in res.items()}
