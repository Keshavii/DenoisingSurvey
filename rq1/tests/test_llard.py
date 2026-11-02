"""Tests for the LLaRD adapter (rq1kit/llard.py). CPU, about a minute.

  cd ~/rq1-kit && python tests/test_llard.py [path to the authors' LLaRD repository]

1. Against the authors' code (LLaRD.py: LLaRD.calculate_LLaRD_loss and its helpers; load_dataset.py: Dataset.get_ui_matrix,
   get_uu_i_matrix; run_LLaRD.eval_test), imported as published, with `.cuda()` of the profile embeddings made a no-op on a
   machine without a GPU: the two normalised graphs, the total loss, the gradients of the embedding tables, the profile MLP
   and the edge scorer, and the evaluation embeddings, on the same batch, the same random gate and the same weights.
   Skipped with a notice if the repository is absent.
2. End to end on a tiny dataset with synthetic knowledge files: trains, exports top-K lists with no seen-item leak,
   identical reruns, a clear error when the knowledge for a training file is missing, grid keys valid.
"""
import json
import os
import pickle
import subprocess
import sys
import tempfile
import types

import numpy as np
import torch

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT)
sys.path.insert(0, os.path.join(KIT, "tests"))
from rq1kit.llard import LLaRDNet, build_graphs, build_name  # noqa: E402
from test_partc import make_dataset  # noqa: E402

PY = [sys.executable, "-m"]
ENV = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONPATH": KIT}
AUTHORS = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/repos/LLaRD")
if not os.path.isdir(AUTHORS):
    AUTHORS = "/home/claude/ext/LLaRD"


def toy_knowledge(nu, ni, users, items, seed=0):
    rng = np.random.default_rng(seed)
    hist = {u: [] for u in range(nu)}
    for u, i in zip(users, items):
        hist[int(u)].append(int(i))
    aug, uu = {}, {}
    for u in range(nu):
        h = list(hist[u])
        if len(h) > 1 and rng.random() < 0.7:
            h.pop(int(rng.integers(len(h))))
        if rng.random() < 0.8:
            h.append(int(rng.integers(ni)))  # may duplicate an existing edge, as in the authors' data
        aug[u] = h
        uu[u] = [int(rng.integers(nu))] if rng.random() < 0.8 else []
    return aug, uu


def test_matches_authors():
    if not os.path.isfile(os.path.join(AUTHORS, "LLaRD.py")):
        print("skip  authors' repository not found, comparison not run")
        return
    sys.path.insert(0, AUTHORS)
    if not torch.cuda.is_available():
        torch.Tensor.cuda = lambda self, *a, **k: self  # stand-in: the authors' load_embedding moves tensors with .cuda()
    import LLaRD as AL
    import load_dataset as AD
    dev = torch.device("cpu")
    nu, ni, d, B = 30, 40, 8, 16
    rng = np.random.default_rng(0)
    pairs = np.unique(np.stack([rng.integers(0, nu, 300), rng.integers(0, ni, 300)], 1), axis=0)
    users, items = pairs[:, 0].astype(np.int64), pairs[:, 1].astype(np.int64)
    aug, uu = toy_knowledge(nu, ni, users, items)

    ds = AD.Dataset.__new__(AD.Dataset)
    ds.device, ds.num_user, ds.num_item, ds.num_node = dev, nu, ni, nu + ni
    ds.training_user, ds.training_item = users.tolist(), items.tolist()
    ds.aug_training_user = [u for u, its in aug.items() for _ in its]
    ds.aug_training_item = [i for its in aug.values() for i in its]
    ds.social_i = [u for u, vs in uu.items() for _ in vs]
    ds.social_j = [v for vs in uu.values() for v in vs]
    adj_t, cf_index = ds.get_ui_matrix()
    aug_t, _ = ds.get_uu_i_matrix()
    adj_m, aug_m = build_graphs(nu, ni, users, items, aug, uu, dev)
    assert torch.allclose(adj_t.to_dense(), adj_m.to_dense(), atol=1e-7), "training graph differs"
    assert torch.allclose(aug_t.to_dense(), aug_m.to_dense(), atol=1e-7), "knowledge graph differs"
    assert torch.equal(adj_t.indices(), adj_m.indices()) and torch.equal(cf_index.t(), adj_m.indices()), "edge order differs"

    tmp = tempfile.mkdtemp(prefix="llard_auth_")
    os.makedirs(os.path.join(tmp, "prf_k"))
    prf_dim = 12
    up, ip = np.random.default_rng(1).standard_normal((nu, prf_dim)).astype(np.float32), np.random.default_rng(2).standard_normal((ni, prf_dim)).astype(np.float32)
    pickle.dump(up, open(os.path.join(tmp, "prf_k/usr_emb_np.pkl"), "wb"))
    pickle.dump(ip, open(os.path.join(tmp, "prf_k/itm_emb_np.pkl"), "wb"))
    args = types.SimpleNamespace(num_user=nu, num_item=ni, model="LGN", gcn_layer=2, latent_dim=d, init_type="norm", l2_reg=1e-4,
                                 beta=5.0, alpha=0.1, sigma=0.25, keep_rate=0.8, edge_bias=0.5, batch_size=B, prf_weight=0.01,
                                 str_weight=1.0, kd_temperature=0.2, device_id="0", data_path=tmp + "/")

    class DS:
        def get_ui_matrix(self):
            return adj_t, cf_index

        def get_uu_i_matrix(self):
            return aug_t, []

    torch.manual_seed(3)
    theirs = AL.LLaRD(args, DS())
    mine = LLaRDNet(nu, ni, adj_m, aug_m, torch.tensor(up), torch.tensor(ip), d, 2, 1e-4, 5.0, 0.1, 0.25, 0.5, B, 0.01, 1.0, 0.2)
    mine.load_state_dict(theirs.state_dict())
    g = torch.Generator().manual_seed(6)
    u = torch.randint(0, nu, (B,), generator=g)
    p = torch.randint(0, ni, (B,), generator=g)
    n = torch.randint(0, ni, (B,), generator=g)
    for sd in (11, 12):
        torch.manual_seed(sd)
        _, _, _, _, _, loss_t = theirs.calculate_LLaRD_loss([u.numpy(), p.numpy(), n.numpy()])
        gt = torch.autograd.grad(loss_t, [theirs.user_embeddings.weight, theirs.item_str_embeddings.weight, theirs.mlp[0].weight,
                                          theirs.linear_1.weight, theirs.linear_2.weight])
        torch.manual_seed(sd)
        loss_m, parts = mine.loss(u, p, n)
        gm = torch.autograd.grad(loss_m, [mine.user_embeddings.weight, mine.item_str_embeddings.weight, mine.mlp[0].weight,
                                          mine.linear_1.weight, mine.linear_2.weight])
        assert torch.allclose(loss_t, loss_m, rtol=1e-5, atol=1e-7), (sd, loss_t.item(), loss_m.item())
        for a_, b_ in zip(gt, gm):
            assert (a_ - b_).abs().max().item() <= 1e-4 * a_.abs().max().item() + 1e-9, "gradients differ"
    theirs.eval(); mine.eval()
    torch.manual_seed(21)
    with torch.no_grad():
        ut, it = theirs.forward(theirs.graph_learner(theirs.user_embeddings, theirs.item_embeddings), g_type="cf")
    torch.manual_seed(21)
    um, im = mine.propagate()
    assert torch.allclose(ut, um, atol=1e-6) and torch.allclose(it, im, atol=1e-6), "evaluation embeddings differ"
    print("ok  both normalised graphs (with duplicate and one-directional edges), total loss, gradients of tables / MLP / edge scorer, and evaluation embeddings identical to the authors' LLaRD (2 gates)")


def run(args, cwd, ok=True):
    out = subprocess.run(PY + args, cwd=cwd, capture_output=True, text=True, env=ENV)
    if ok:
        assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]
    return out


def test_end_to_end():
    root = tempfile.mkdtemp(prefix="llard_test_")
    make_dataset(os.path.join(root, "data/tiny"), 4, n_users=60)
    meta = json.load(open(f"{root}/data/tiny/meta.json"))
    nu, ni = meta["n_users"], meta["n_items"]
    import pandas as pd
    tr = pd.read_csv(f"{root}/data/tiny/train_N2_20_s1.tsv", sep="\t")
    tr = tr[["user", "item"]] if "user" in tr.columns else tr.iloc[:, :2].set_axis(["user", "item"], axis=1)
    aug, uu = toy_knowledge(nu, ni, tr["user"].values, tr["item"].values, seed=5)
    kd = f"{root}/data/tiny/llard/N2_20_s1"
    os.makedirs(f"{kd}/prf_k"); os.makedirs(f"{kd}/rel_k")
    pickle.dump(np.random.default_rng(1).standard_normal((nu, 12)).astype(np.float32), open(f"{kd}/prf_k/usr_emb_np.pkl", "wb"))
    pickle.dump(np.random.default_rng(2).standard_normal((ni, 12)).astype(np.float32), open(f"{kd}/prf_k/itm_emb_np.pkl", "wb"))
    np.save(f"{kd}/rel_k/aug_traindata.npy", np.array(aug, dtype=object), allow_pickle=True)
    np.save(f"{kd}/rel_k/uu_data.npy", np.array(uu, dtype=object), allow_pickle=True)
    common = ["--data", "data/tiny", "--model", "lightgcn", "--lr", "0.005", "--lr_mult", "2", "--reg", "0.0001", "--epochs", "4",
              "--min_epochs", "1", "--patience", "10", "--seed", "1", "--device", "cpu", "--batch", "64", "--dim", "16", "--layers", "2"]
    run(["rq1kit.llard", *common, "--train_file", "train_N2_20_s1.tsv", "--run_dir", "runs/a"], root)
    run(["rq1kit.llard", *common, "--train_file", "train_N2_20_s1.tsv", "--run_dir", "runs/b", "--no_export"], root)
    info = json.load(open(f"{root}/runs/a/run.json"))
    assert abs(info["lr_effective"] - 0.01) < 1e-12, info
    ha = [json.loads(x) for x in open(f"{root}/runs/a/history.jsonl")]
    hb = [json.loads(x) for x in open(f"{root}/runs/b/history.jsonl")]
    assert len(ha) == 4 and all(x["valid_clean_ndcg@20"] == y["valid_clean_ndcg@20"] for x, y in zip(ha, hb)), (ha, hb)
    run(["rq1kit.evaluate", "--data", "data/tiny", "--train_file", "train_N2_20_s1.tsv", "--topk", "runs/a/topk_test.npy",
         "--out", "results/llard.json", "--tag", "method=LLaRD"], root)
    r = json.load(open(f"{root}/results/llard.json"))
    assert r["seen_item_leak_rate"] == 0
    out = run(["rq1kit.llard", *common, "--train_file", "train_N2_20_s2.tsv", "--run_dir", "runs/c"], root, ok=False)
    assert out.returncode != 0 and "LLM knowledge" in (out.stdout + out.stderr), "missing knowledge not reported"
    assert build_name("train.tsv") == "N0" and build_name("train_N2_20_s3.tsv") == "N2_20_s3"
    cfg = json.load(open(os.path.join(KIT, "configs/partc/methods/llard.json")))
    assert cfg["datasets"] == ["ml1m"] and len(cfg["grid"]) == 8 and all(set(x) == {"lr_mult", "alpha", "beta"} for x in cfg["grid"])
    print(f"ok  end to end: lr 0.005 x 2 = 0.01, reruns identical, test NDCG@20 {r['ndcg@20']:.4f}, no leak, missing knowledge reported, grid keys valid")


if __name__ == "__main__":
    test_matches_authors()
    test_end_to_end()
    print("ALL LLARD TESTS PASSED")
