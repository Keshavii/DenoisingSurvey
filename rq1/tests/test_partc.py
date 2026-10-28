"""End-to-end test of the Part C pipeline on two tiny synthetic datasets (CPU, a few minutes).

  cd ~/rq1-kit && python tests/test_partc.py

Checks: full run until idle (canary -> tuning -> automatic pick -> finals -> evaluation), picks, results with no
seen-item leak, adoption of existing outputs after the state file is lost, conflict detection when an output does
not match the plan, retry, canary hold, failure classification, and waiting while an rq1kit.queue process runs.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np
import pandas as pd

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT)
from rq1kit import partc as P  # noqa: E402


def make_dataset(folder, seed, n_users=40, n_items=30, per_user=8):
    rng = np.random.default_rng(seed)
    tr, vc, vn, te = [], [], [], []
    for u in range(n_users):
        items = rng.choice(n_items, per_user, replace=False)
        for i in items[:6]:
            tr.append((u, i, int(rng.random() < 0.3), -1))
        vc.append((u, items[6], -1))
        vn.append((u, items[6], 0, -1))
        te.append((u, items[7], -1))
    os.makedirs(folder)
    train = pd.DataFrame(tr, columns=["user", "item", "noisy", "ts"])
    train.to_csv(f"{folder}/train.tsv", sep="\t", index=False)
    train[train.noisy == 0].to_csv(f"{folder}/train_clean.tsv", sep="\t", index=False)
    pd.DataFrame(vc, columns=["user", "item", "ts"]).to_csv(f"{folder}/valid_clean.tsv", sep="\t", index=False)
    pd.DataFrame(vn, columns=["user", "item", "noisy", "ts"]).to_csv(f"{folder}/valid_noisy.tsv", sep="\t", index=False)
    pd.DataFrame(te, columns=["user", "item", "ts"]).to_csv(f"{folder}/test.tsv", sep="\t", index=False)
    for s in (1, 2):
        seen = set(zip(train.user, train.item)) | {(u, i) for u, i, _ in vc} | {(u, i) for u, i, _ in te}
        extra = []
        r = np.random.default_rng(100 + s)
        while len(extra) < len(train) // 5:
            u, i = int(r.integers(n_users)), int(r.integers(n_items))
            if (u, i) not in seen:
                seen.add((u, i))
                extra.append((u, i, 2, -1))
        pd.concat([train, pd.DataFrame(extra, columns=train.columns)]).to_csv(f"{folder}/train_N2_20_s{s}.tsv", sep="\t", index=False)
    json.dump({"n_users": n_users, "n_items": n_items, "split_rule": "synthetic"}, open(f"{folder}/meta.json", "w"))


def make_root(min_ratio=0.0):
    root = tempfile.mkdtemp(prefix="partc_test_")
    os.symlink(os.path.join(KIT, "rq1kit"), os.path.join(root, "rq1kit"))
    os.makedirs(os.path.join(root, "configs/partc/methods"))
    proto = json.load(open(os.path.join(KIT, "configs/partc/protocol.json")))
    proto.update(datasets=["tinya", "tinyb"], dataset_slots={"tinya": 1, "tinyb": 2}, total_slots=2, threads_per_job=1, min_free_disk_gb=1,
                 seeds=[1, 2], final_extra_args="--epochs 4 --patience 2 --device cpu",
                 canary={"dataset": "tinya", "min_ratio_to_plain": min_ratio})
    proto["tune"].update(epochs=3)
    json.dump(proto, open(os.path.join(root, "configs/partc/protocol.json"), "w"), indent=2)
    for name in ("tce", "rce"):
        m = json.load(open(os.path.join(KIT, f"configs/partc/methods/{name}.json")))
        m.update(datasets=["tinya", "tinyb"], grid=m["grid"][:2])
        json.dump(m, open(os.path.join(root, f"configs/partc/methods/{name}.json"), "w"), indent=2)
    bp = {f"{ds}|{mod}|bce": {"lr": 0.01, "reg": 0.0001, "valid_ndcg@20": 0.05} for ds in ("tinya", "tinyb") for mod in ("lightgcn", "mf")}
    json.dump(bp, open(os.path.join(root, "configs/best_plain.json"), "w"))
    make_dataset(os.path.join(root, "data/tinya"), 1)
    make_dataset(os.path.join(root, "data/tinyb"), 2, n_users=50)
    return root


def partc(root, *args, check=True):
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": ""}
    r = subprocess.run([sys.executable, "-m", "rq1kit.partc", *args], cwd=root, capture_output=True, text=True, env=env)
    if check and r.returncode != 0:
        raise AssertionError(f"partc {' '.join(args)} failed:\n{r.stdout}\n{r.stderr}")
    return r.stdout


def state_of(root):
    cwd = os.getcwd()
    os.chdir(root)
    try:
        proto, methods, bp, jobs, waiting, st, canary, picks = P.snapshot()
    finally:
        os.chdir(cwd)
    return jobs, waiting, st, canary, picks


def test_failure_classes():
    assert P.classify_failure("RuntimeError: CUDA out of memory. Tried to allocate", 1) == "alone"
    assert P.classify_failure("", -9) == "alone" and P.classify_failure("", 137) == "alone"
    assert P.classify_failure("CUDA error: unspecified launch failure", 1) == "again"
    assert P.classify_failure("KeyError: 'x'", 1) is None
    print("ok  failure classes")


def test_full_run_adoption_conflict_retry():
    root = make_root()
    print(partc(root, "check"), end="")
    t0 = time.time()
    out = partc(root, "run", "--until-idle", "--poll", "0.5")
    jobs, waiting, st, canary, picks = state_of(root)
    n_tune, n_final = 2 * 2 * 2, 2 * 2 * 2 * 3
    assert len([j for j in jobs if j["stage"] != "final"]) == n_tune, len(jobs)
    assert len([j for j in jobs if j["stage"] == "final"]) == n_final and not waiting
    bad = {k: v for k, v in st.items() if v["status"] != "done"}
    assert not bad, (bad, out[-2000:])
    for m in ("tce", "rce"):
        assert canary[m][0] == "passed", canary
        p = json.load(open(os.path.join(root, f"configs/partc/best/{m}.json")))
        assert set(p) == {"tinya", "tinyb"}, p
    for j in jobs:
        if j["stage"] == "final":
            r = json.load(open(os.path.join(root, j["output"])))
            assert r["seen_item_leak_rate"] == 0 and r["method"] in ("T-CE", "R-CE"), r
    print(f"ok  full run: {n_tune} tuning + {n_final} final jobs in {time.time() - t0:.0f}s, picks written, no leak")
    print(partc(root, "status"), end="")

    # the state file is lost: everything must be adopted from the outputs, nothing rerun
    os.rename(os.path.join(root, P.STATE), os.path.join(root, P.STATE + ".bak"))
    jobs, waiting, st, canary, picks = state_of(root)
    assert all(v["status"] == "done" for v in st.values()), [k for k, v in st.items() if v["status"] != "done"]
    ev = [json.loads(line)["event"] for line in open(os.path.join(root, P.STATE))]
    assert ev.count("adopted") == n_tune + n_final, ev[:5]
    print("ok  adoption: all", n_tune + n_final, "outputs adopted after losing the state file")

    # an output that does not match the plan is a conflict and is not overwritten
    j = next(j for j in jobs if j["stage"] == "final")
    rjp = os.path.join(root, j["run_dir"], "run.json")
    rj = json.load(open(rjp))
    rj["lr"] = 0.5
    json.dump(rj, open(rjp, "w"))
    os.remove(os.path.join(root, P.STATE))
    jobs, waiting, st, canary, picks = state_of(root)
    assert st[j["id"]]["status"] == "conflict" and "lr" in st[j["id"]]["reason"], st[j["id"]]
    assert sum(v["status"] == "conflict" for v in st.values()) == 1
    before = os.path.getmtime(os.path.join(root, j["output"]))
    partc(root, "run", "--until-idle", "--poll", "0.5")
    assert os.path.getmtime(os.path.join(root, j["output"])) == before, "a conflicting output was overwritten"
    print("ok  conflict: mismatching output detected (", st[j["id"]]["reason"][:60], ") and left alone")

    partc(root, "retry", j["id"])
    partc(root, "run", "--until-idle", "--poll", "0.5")
    jobs, waiting, st, canary, picks = state_of(root)
    assert st[j["id"]]["status"] == "done" and json.load(open(rjp))["lr"] == 0.01
    print("ok  retry: the conflicting job reran after `partc retry` and now matches the plan")
    show = partc(root, "show", "tce")
    assert "canary: passed" in show
    shutil.rmtree(root)


def test_legacy_queue_only_canaries():
    root = make_root()
    sleeper_start = time.time()
    sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(25)", "python -m rq1kit.queue --jobs x"])
    partc(root, "run", "--until-idle", "--poll", "0.5")
    sleeper.wait()
    starts = [json.loads(line) for line in open(os.path.join(root, P.STATE)) if '"start"' in line]
    jobs, waiting, st, canary, picks = state_of(root)
    stage = {j["id"]: j["stage"] for j in jobs}
    sleeper_end = sleeper_start + 25
    early = [r for r in starts if time.mktime(time.strptime(r["t"], "%Y-%m-%d %H:%M:%S")) < sleeper_end - 1]
    assert early and all(stage[r["job"]] == "canary" for r in early), [(r["job"], r["t"]) for r in early]
    assert all(v["status"] == "done" for v in st.values())
    print(f"ok  queue running: only canaries started ({', '.join(r['job'] for r in early)}); the rest after it ended")
    shutil.rmtree(root)


def test_legacy_queue_shared_gpu():
    root = make_root()
    json.dump({"slots_taken_by_legacy_queue": 1}, open(os.path.join(root, "configs/partc/scheduler.json"), "w"))
    t0 = time.time()
    sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(40)", "python -m rq1kit.queue --jobs x"])
    partc(root, "run", "--until-idle", "--poll", "0.5")
    sleeper.wait()
    starts = [json.loads(line) for line in open(os.path.join(root, P.STATE)) if '"start"' in line]
    jobs, waiting, st, canary, picks = state_of(root)
    stage = {j["id"]: j["stage"] for j in jobs}
    early = [r for r in starts if time.mktime(time.strptime(r["t"], "%Y-%m-%d %H:%M:%S")) < t0 + 38]
    assert any(stage[r["job"]] != "canary" for r in early), "no tuning/final job started while the queue ran"
    assert all(r["slots"] <= 1 for r in early), [(r["job"], r["slots"]) for r in early]
    assert all(v["status"] == "done" for v in st.values())
    print(f"ok  shared GPU: {len(early)} jobs started while the queue ran, none needing more than the 1 free slot")
    shutil.rmtree(root)


def test_canary_hold():
    root = make_root(min_ratio=1e9)
    partc(root, "run", "--until-idle", "--poll", "0.5")
    starts = [json.loads(line) for line in open(os.path.join(root, P.STATE)) if '"start"' in line]
    jobs, waiting, st, canary, picks = state_of(root)
    ran = {r["job"] for r in starts}
    assert ran == {"tune_tinya_tce_t0", "tune_tinya_rce_t0"}, ran
    assert canary["tce"][0] == "held" and canary["rce"][0] == "held", canary
    assert "HELD" in partc(root, "status")
    print("ok  canary hold: only the two canaries ran; both methods held:", canary["tce"][1][:70])
    shutil.rmtree(root)


if __name__ == "__main__":
    test_failure_classes()
    test_canary_hold()
    test_legacy_queue_only_canaries()
    test_legacy_queue_shared_gpu()
    test_full_run_adoption_conflict_retry()
    print("ALL PARTC TESTS PASSED")
