"""Part C pipeline: one self-running driver for every method x dataset x backbone x condition x seed.

Run from the kit folder (rq1/, i.e. ~/rq1-kit on PC 1) with the rq1 environment active:

  python -m rq1kit.partc check [--write-lock]   environment, data, baselines, disk, GPU; refuses on problems
  python -m rq1kit.partc plan                   print what would run now (nothing is started)
  python -m rq1kit.partc run [--until-idle]     the driver loop (normally the systemd service `partc`)
  python -m rq1kit.partc status                 one table: canary, tuning, pick, finals per method x dataset
  python -m rq1kit.partc show <method|job_id>   exact settings, picks, state and log tail
  python -m rq1kit.partc retry <method|job_id>  clear a failure, a held canary or a conflict so it runs again
  python -m rq1kit.partc collect                rebuild tables/ from results/
  python -m rq1kit.partc install                write and enable the systemd user service `partc`

What it does, per method (configs/partc/methods/<method>.json) and dataset:
  canary   the first tuning trial on the canary dataset; the method's other jobs wait for it and run only if it
           finishes, writes its files and reaches min_ratio_to_plain x the plain model's validation NDCG@20
  tune     the method's grid (at most protocol.tune.max_trials points) on LightGCN, natural data, seed 0
  pick     automatic: highest clean-validation NDCG@20 (ties: earliest grid point) -> configs/partc/best/<method>.json
  final    picked settings x protocol.seeds x protocol.conditions (backbones the method applies to), then evaluate

Rules that keep results consistent:
  * A job's identity is its command; its hash is the hash of that command. A job is done only when a state record
    with the same hash says so and its output file exists. Change a grid, a pick or the protocol and only the jobs
    whose commands change run again.
  * Outputs that exist without a state record (runs made by rq1kit.queue before this pipeline) are adopted only if
    every argument in their run.json matches the planned command; otherwise they are marked as conflicts and left
    alone until `retry`, so no result is ever overwritten silently.
  * While an rq1kit.queue process is running, the driver starts nothing new (the two would run the same jobs).
  * Out of GPU memory or killed for RAM: retried once, alone on the GPU. Known transient CUDA errors: retried once.
    Anything else: marked failed with its log tail; the rest of the queue continues.
"""
import argparse
import fcntl
import glob
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
from collections import Counter, defaultdict

PROTOCOL = "configs/partc/protocol.json"
METHODS = "configs/partc/methods"
BEST_DIR = "configs/partc/best"
BEST_PLAIN = "configs/best_plain.json"
ENV_LOCK = "configs/partc/env.lock.json"
DATA_LOCK = "configs/partc/data.lock.json"
LOGDIR = "logs/partc"
STATE = "logs/partc/state.jsonl"
JOBLOGS = "logs/partc/jobs"
STATUS = "logs/partc/status.txt"
LOCK = "logs/partc/driver.lock"
STAGE_RANK = {"canary": 0, "tune": 1, "final": 2}
OOM_MARKERS = ("CUDA out of memory", "OutOfMemoryError", "CUBLAS_STATUS_ALLOC_FAILED", "cuDNN error: CUDNN_STATUS_ALLOC")
TRANSIENT_MARKERS = ("unspecified launch failure", "CUDA error: launch timeout", "uncorrectable ECC error")


# ----------------------------------------------------------------------------------------------- configuration
def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def load_protocol():
    return load_json(PROTOCOL)


def load_methods():
    ms = [load_json(f) for f in sorted(glob.glob(os.path.join(METHODS, "*.json")))]
    return sorted(ms, key=lambda m: (m["batch"], m["name"]))


def margs(params):
    return " ".join(f"--{k} {v}" for k, v in params.items())


def job_hash(cmd):
    return hashlib.sha1(cmd.encode()).hexdigest()[:12]


def canary_dataset(proto, m):
    ds = proto["canary"]["dataset"]
    return ds if ds in m["datasets"] else m["datasets"][0]


def grid_of(proto, m):
    return m["grid"][: proto["tune"]["max_trials"]]


# ----------------------------------------------------------------------------------------------- the job graph
def build_plan(proto, methods, best_plain, picks):
    """All jobs that can be written down now. Finals of a method x dataset appear once its pick exists.
    Returns (jobs, waiting) where waiting lists (method, dataset, n_expected_finals) still without a pick."""
    jobs, waiting, order = [], [], 0
    t = proto["tune"]
    for m in methods:
        cds = canary_dataset(proto, m)
        canary_id = f"tune_{cds}_{m['name']}_t0"
        for ds in [d for d in proto["datasets"] if d in m["datasets"]]:
            key = f"{ds}|{t['model']}|{m['loss']}"
            if key not in best_plain:
                continue  # reported by `check`
            b = best_plain[key]
            slots = proto["dataset_slots"].get(ds, 1)
            tf = "" if t["train_file"] == "train.tsv" else f" --train_file {t['train_file']}"
            for k, g in enumerate(grid_of(proto, m)):
                rd = f"{m['tune_dir']}/{ds}/{m['name']}_t{k}"
                cmd = (f"python -m {m['module']} {m['base_args']} {margs(g)} --data data/{ds}{tf} --model {t['model']} "
                       f"--lr {b['lr']} --reg {b['reg']} --epochs {t['epochs']} --seed {t['seed']} --no_export --run_dir {rd}")
                jid = f"tune_{ds}_{m['name']}_t{k}"
                stage = "canary" if jid == canary_id else "tune"
                jobs.append(dict(id=jid, method=m["name"], dataset=ds, stage=stage, cmd=cmd, slots=slots, run_dir=rd,
                                 output=f"{rd}/run.json", deps=[] if stage == "canary" else [canary_id],
                                 batch=m["batch"], order=order, trial=k))
                order += 1
            pick = picks.get(m["name"], {}).get(ds)
            conds = [c for c in proto["conditions"] if c["model"] in m["backbones"]]
            if not pick:
                waiting.append((m["name"], ds, len(conds) * len(proto["seeds"])))
                continue
            params = {k: pick[k] for k in m["grid"][0]}
            for s in proto["seeds"]:
                for c in conds:
                    trf = c["train_file"].format(seed=s)
                    bb = best_plain[f"{ds}|{c['model']}|{m['loss']}"]
                    name = f"{m['name']}_{c['model']}_{c['cond']}_s{s}"
                    rd, res = f"runs/{ds}/{name}", f"results/C/{ds}/{name}.json"
                    extra = f" {proto['final_extra_args']}" if proto.get("final_extra_args") else ""
                    train = (f"python -m {m['module']} {m['base_args']} {margs(params)} --data data/{ds} --train_file {trf} "
                             f"--model {c['model']} --lr {bb['lr']} --reg {bb['reg']} --seed {s} --run_dir {rd}{extra}")
                    ev = (f"python -m rq1kit.evaluate --data data/{ds} --train_file {trf} --topk {rd}/topk_test.npy --out {res} "
                          f"--tag part=C dataset={ds} method={m['display']} backbone={proto['backbone_names'][c['model']]} "
                          f"cond={c['cond']} seed={s} train_file={trf}")
                    jobs.append(dict(id=f"{ds}_{name}", method=m["name"], dataset=ds, stage="final",
                                     cmd=f'bash -c "{train} && {ev}"', slots=slots, run_dir=rd, output=res, deps=[],
                                     batch=m["batch"], order=order, tags=dict(dataset=ds, method=m["display"],
                                                                               cond=c["cond"], seed=str(s))))
                    order += 1
    for j in jobs:
        j["hash"] = job_hash(j["cmd"])
    return jobs, waiting


def train_argv(cmd):
    """The training command's --key value pairs (flags without a value -> True)."""
    toks = shlex.split(cmd)
    if toks[:2] == ["bash", "-c"]:
        toks = shlex.split(toks[2].split(" && ")[0])
    out, i = {}, 0
    while i < len(toks):
        if toks[i].startswith("--"):
            k = toks[i][2:]
            if i + 1 < len(toks) and not toks[i + 1].startswith("--"):
                out[k], i = toks[i + 1], i + 2
            else:
                out[k], i = True, i + 1
        else:
            i += 1
    return out


def same_value(planned, stored):
    if planned is True:
        return stored is True
    try:
        return float(planned) == float(stored)
    except (TypeError, ValueError):
        return str(planned) == str(stored)


def verify_existing(job):
    """For an output made outside this pipeline: (True, None) if it provably came from this exact command."""
    rj = load_json(os.path.join(job["run_dir"], "run.json"))
    if rj is None:
        return False, "run.json missing"
    bad = [k for k, v in train_argv(job["cmd"]).items() if k not in rj or not same_value(v, rj[k])]
    if bad:
        return False, "differs from plan in: " + ", ".join(f"{k} (run {rj.get(k)!r} vs plan {train_argv(job['cmd'])[k]!r})" for k in bad[:4])
    if job["stage"] == "final":
        res = load_json(job["output"]) or {}
        badt = [k for k, v in job["tags"].items() if str(res.get(k)) != v]
        if badt:
            return False, "result tags differ: " + ", ".join(badt)
        if res.get("seen_item_leak_rate", 0) > 0:
            return False, f"evaluator reported a seen-item leak of {res['seen_item_leak_rate']}"
    return True, None


# ----------------------------------------------------------------------------------------------- state
def append_state(rec):
    os.makedirs(LOGDIR, exist_ok=True)
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), **rec}
    with open(STATE, "a") as f:
        f.write(json.dumps(rec) + "\n")


def read_state():
    recs = []
    if os.path.exists(STATE):
        with open(STATE) as f:
            recs = [json.loads(line) for line in f if line.strip()]
    return recs


def derive(jobs, recs, running_ids=()):
    """Status per job: done | running | failed | conflict | retry | todo (only records with the job's current hash count)."""
    by = defaultdict(list)
    for r in recs:
        by[r["job"]].append(r)
    st = {}
    for j in jobs:
        s = dict(status="todo", fails=0, reason=None, seconds=None, retry=None, reset=False)
        for r in by.get(j["id"], []):
            if r.get("hash") != j["hash"]:
                continue
            ev = r["event"]
            if ev in ("ok", "adopted"):
                s.update(status="done", seconds=r.get("seconds"), reason=None, reset=False)
            elif ev == "fail":
                s["fails"] += 1
                s.update(status="retry" if (r.get("retry") and s["fails"] == 1) else "failed",
                         reason=r.get("reason"), retry=r.get("retry"))
            elif ev == "conflict":
                s.update(status="conflict", reason=r.get("reason"))
            elif ev == "reset":  # `partc retry`: run again even though an output exists
                s.update(status="todo", fails=0, reason=None, retry=None, reset=True)
        if s["status"] == "done" and not os.path.exists(j["output"]):
            s.update(status="todo", reason="output missing")
        if j["id"] in running_ids:
            s["status"] = "running"
        st[j["id"]] = s
    return st


def adopt(jobs, st):
    """Record outputs that already exist (made by rq1kit.queue) after checking them against the plan."""
    n = 0
    for j in jobs:
        if st[j["id"]]["status"] != "todo" or st[j["id"]]["reset"] or not os.path.exists(j["output"]):
            continue
        ok, why = verify_existing(j)
        if ok:
            rj = load_json(os.path.join(j["run_dir"], "run.json")) or {}
            secs = (rj.get("train_seconds") or 0) + (rj.get("export_seconds") or 0)
            append_state(dict(job=j["id"], hash=j["hash"], event="adopted", seconds=round(secs, 1)))
            st[j["id"]].update(status="done", seconds=secs)
            n += 1
        else:
            append_state(dict(job=j["id"], hash=j["hash"], event="conflict", reason=why))
            st[j["id"]].update(status="conflict", reason=why)
    return n


# ----------------------------------------------------------------------------------------------- canary and picks
def canary_state(proto, m, jobs, st, best_plain):
    """('passed'|'pending'|'held', reason)."""
    cj = next((j for j in jobs if j["method"] == m["name"] and j["stage"] == "canary"), None)
    if cj is None:
        return "pending", "no canary planned"
    s = st[cj["id"]]
    if s["status"] in ("failed", "conflict"):
        return "held", f"canary {s['status']}: {s['reason']}"
    if s["status"] != "done":
        return "pending", None
    rj = load_json(os.path.join(cj["run_dir"], "run.json")) or {}
    missing = [f for f in ("run.json", "history.jsonl", "best.pt") if not os.path.exists(os.path.join(cj["run_dir"], f))]
    if missing:
        return "held", "canary files missing: " + ", ".join(missing)
    plain = best_plain[f"{cj['dataset']}|{proto['tune']['model']}|{m['loss']}"]["valid_ndcg@20"]
    need = proto["canary"]["min_ratio_to_plain"] * plain
    got = rj.get("best_valid_ndcg@20", -1)
    if got < need:
        return "held", f"canary valid NDCG@20 {got:.4f} < {need:.4f} ({proto['canary']['min_ratio_to_plain']} x plain {plain:.4f})"
    return "passed", f"valid NDCG@20 {got:.4f} (plain {plain:.4f})"


def compute_picks(proto, methods, jobs, st):
    """Best tuning trial per method x dataset once all its trials are done; written to configs/partc/best/."""
    picks = {}
    for m in methods:
        cur = load_json(os.path.join(BEST_DIR, f"{m['name']}.json"), {})
        new = {}
        for ds in m["datasets"]:
            tj = [j for j in jobs if j["method"] == m["name"] and j["dataset"] == ds and j["stage"] in ("canary", "tune")]
            if not tj or any(st[j["id"]]["status"] != "done" for j in tj):
                continue
            best = None
            for j in sorted(tj, key=lambda j: j["trial"]):
                rj = load_json(os.path.join(j["run_dir"], "run.json"))
                v = rj["best_valid_ndcg@20"]
                if best is None or v > best[0]:
                    best = (v, j, rj)
            v, j, rj = best
            new[ds] = {**grid_of(proto, m)[j["trial"]], "valid_ndcg@20": v, "best_epoch": rj["best_epoch"],
                       "trial": f"{m['name']}_t{j['trial']}"}
        if new != cur and new:
            os.makedirs(BEST_DIR, exist_ok=True)
            with open(os.path.join(BEST_DIR, f"{m['name']}.json"), "w") as f:
                json.dump(new, f, indent=2, sort_keys=True)
        picks[m["name"]] = new
    return picks


def snapshot():
    """Plan + state as of now (adopting existing outputs on the way)."""
    proto, methods = load_protocol(), load_methods()
    best_plain = load_json(BEST_PLAIN, {})
    recs = read_state()
    picks = {m["name"]: load_json(os.path.join(BEST_DIR, f"{m['name']}.json"), {}) for m in methods}
    for _ in range(3):  # picks can unlock finals, which can be adopted, which changes nothing further
        jobs, waiting = build_plan(proto, methods, best_plain, picks)
        st = derive(jobs, read_state())
        adopt(jobs, st)
        new_picks = compute_picks(proto, methods, jobs, st)
        if new_picks == picks:
            break
        picks = new_picks
    canary = {m["name"]: canary_state(proto, m, jobs, st, best_plain) for m in methods}
    return proto, methods, best_plain, jobs, waiting, st, canary, picks


# ----------------------------------------------------------------------------------------------- helpers
def legacy_queue_running():
    try:
        out = subprocess.run(["pgrep", "-f", "rq1kit.queue"], capture_output=True, text=True).stdout.split()
    except FileNotFoundError:
        return []
    return [p for p in out if int(p) != os.getpid()]


def kit_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=10).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def gpu_line():
    try:
        return subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader"],
                              capture_output=True, text=True, timeout=10).stdout.strip() or "no GPU"
    except Exception:
        return "no GPU"


def classify_failure(log_tail, returncode):
    """'alone' (GPU or RAM out of memory), 'again' (known transient CUDA error) or None."""
    if any(mk in log_tail for mk in OOM_MARKERS) or returncode in (-9, 137):
        return "alone"
    if any(mk in log_tail for mk in TRANSIENT_MARKERS):
        return "again"
    return None


def tail(path, n=20):
    if not os.path.exists(path):
        return ""
    with open(path, errors="replace") as f:
        return "".join(f.readlines()[-n:])


# ----------------------------------------------------------------------------------------------- run
def runnable(proto, jobs, st, canary):
    done = {jid for jid, s in st.items() if s["status"] == "done"}
    out = []
    for j in jobs:
        s = st[j["id"]]
        if s["status"] not in ("todo", "retry"):
            continue
        if canary[j["method"]][0] == "held" and j["stage"] != "canary":
            continue
        if j["stage"] != "canary" and canary[j["method"]][0] != "passed":
            continue
        if any(d not in done for d in j["deps"]):
            continue
        need = proto["total_slots"] if s["status"] == "retry" and s["retry"] == "alone" else min(j["slots"], proto["total_slots"])
        out.append((j, need))
    out.sort(key=lambda x: (x[0]["batch"], STAGE_RANK[x[0]["stage"]], -x[0]["slots"], x[0]["order"]))
    return out


def cmd_run(a):
    os.makedirs(JOBLOGS, exist_ok=True)
    lockf = open(LOCK, "w")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit("another partc driver is already running (logs/partc/driver.lock)")
    running = {}  # job id -> (Popen, job, need, t0, logfile)
    stopping = {"flag": False}

    def stop(signum, frame):
        stopping["flag"] = True
        for p, *_ in running.values():
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    last_status, commit = 0.0, kit_commit()
    print(f"partc driver started (kit {commit})", flush=True)
    while not stopping["flag"]:
        # finished jobs
        for jid in list(running):
            p, j, need, t0, logpath = running[jid]
            if p.poll() is None:
                continue
            secs = round(time.time() - t0, 1)
            if p.returncode == 0 and os.path.exists(j["output"]):
                append_state(dict(job=jid, hash=j["hash"], event="ok", seconds=secs, slots=need, commit=commit))
            else:
                lt = tail(logpath, 40)
                why = "exit 0 but output missing" if p.returncode == 0 else f"exit {p.returncode}: " + (lt.strip().splitlines() or [""])[-1][:200]
                append_state(dict(job=jid, hash=j["hash"], event="fail", seconds=secs, reason=why,
                                  retry=classify_failure(lt, p.returncode), commit=commit))
            print(f"{time.strftime('%H:%M:%S')} end   {jid} rc={p.returncode} {secs}s", flush=True)
            del running[jid]
        proto, methods, best_plain, jobs, waiting, st, canary, picks = snapshot()
        st = derive(jobs, read_state(), running_ids=running.keys())
        legacy = legacy_queue_running()
        ready = [] if legacy else runnable(proto, jobs, st, canary)
        free = proto["total_slots"] - sum(r[2] for r in running.values())
        env = {**os.environ, "OMP_NUM_THREADS": str(proto["threads_per_job"]), "MKL_NUM_THREADS": str(proto["threads_per_job"])}
        commit = kit_commit()
        for j, need in ready:
            if need > free:
                continue
            if os.path.exists(j["output"]):  # a reset job: never let a stale output count as this run's result
                os.remove(j["output"])
            logpath = os.path.join(JOBLOGS, f"{j['id']}.log")
            lf = open(logpath, "a")
            lf.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} kit {commit} hash {j['hash']}\n$ {j['cmd']}\n")
            lf.flush()
            p = subprocess.Popen(shlex.split(j["cmd"]), stdout=lf, stderr=subprocess.STDOUT, env=env, start_new_session=True)
            append_state(dict(job=j["id"], hash=j["hash"], event="start", slots=need, commit=commit))
            running[j["id"]] = (p, j, need, time.time(), logpath)
            free -= need
            print(f"{time.strftime('%H:%M:%S')} start {j['id']} (slots {need})", flush=True)
        if time.time() - last_status > 60:
            with open(STATUS, "w") as f:
                f.write(render_status(proto, methods, jobs, waiting, st, canary, picks, legacy, running))
            last_status = time.time()
        if a.until_idle and not running and not ready and not legacy:
            break
        time.sleep(a.poll)
    for p, *_ in running.values():
        p.wait()
    print("partc driver stopped", flush=True)


# ----------------------------------------------------------------------------------------------- status / show
def eta_text(proto, jobs, waiting, st):
    durs = defaultdict(list)
    for j in jobs:
        s = st[j["id"]]
        if s["status"] == "done" and s["seconds"]:
            durs[("final" if j["stage"] == "final" else "tune", j["dataset"])].append(s["seconds"])
    est = lambda kind, ds: (sorted(durs[(kind, ds)])[len(durs[(kind, ds)]) // 2] if durs[(kind, ds)] else None)
    slot_secs, unknown = 0.0, 0
    for j in jobs:
        if st[j["id"]]["status"] in ("done", "failed", "conflict"):
            continue
        e = est("final" if j["stage"] == "final" else "tune", j["dataset"])
        if e is None:
            unknown += 1
        else:
            slot_secs += e * min(j["slots"], proto["total_slots"])
    for _, ds, n in waiting:
        e = est("final", ds)
        if e is None:
            unknown += n
        else:
            slot_secs += e * n * proto["dataset_slots"].get(ds, 1)
    hours = slot_secs / proto["total_slots"] / 3600
    t = time.strftime("%a %d %b %H:%M", time.localtime(time.time() + hours * 3600))
    return f"rough finish: {t} ({hours:.1f} h of known work" + (f"; {unknown} jobs with no timing yet)" if unknown else ")")


def render_status(proto, methods, jobs, waiting, st, canary, picks, legacy, running=()):
    L = [f"Part C status {time.strftime('%Y-%m-%d %H:%M')}  kit {kit_commit()}",
         f"{'method':8} {'b':1} {'dataset':12} {'canary':7} {'tune':6} {'pick':5} {'finals':7} {'run':3} {'fail':4} {'confl':5}"]
    wait = {(m, ds): n for m, ds, n in waiting}
    tot = Counter()
    for m in methods:
        for ds in [d for d in proto["datasets"] if d in m["datasets"]]:
            mj = [j for j in jobs if j["method"] == m["name"] and j["dataset"] == ds]
            tj = [j for j in mj if j["stage"] != "final"]
            fj = [j for j in mj if j["stage"] == "final"]
            c = Counter(st[j["id"]]["status"] for j in mj)
            tdone = sum(st[j["id"]]["status"] == "done" for j in tj)
            fdone = sum(st[j["id"]]["status"] == "done" for j in fj)
            nfin = len(fj) or wait.get((m["name"], ds), 0)
            cs = canary[m["name"]][0] if ds == canary_dataset(proto, m) else ""
            L.append(f"{m['display']:8} {m['batch']:<1} {ds:12} {cs:7} {tdone:>2}/{len(tj):<3} {'yes' if ds in picks.get(m['name'], {}) else '-':5} "
                     f"{fdone:>3}/{nfin:<3} {c['running']:>3} {c['failed']:>4} {c['conflict']:>5}")
            tot.update(c)
            tot["planned"] += len(tj) + nfin
            tot["done_all"] += tdone + fdone
    L.append(f"total: {tot['done_all']} of {tot['planned']} done, {tot['running']} running, {tot['failed']} failed, "
             f"{tot['conflict']} conflicts; held: {', '.join(m for m, c in canary.items() if c[0] == 'held') or 'none'}")
    L.append(f"GPU: {gpu_line()}" + (f"   rq1kit.queue running (pids {' '.join(legacy)}): partc waits for it" if legacy else ""))
    L.append(eta_text(proto, jobs, waiting, st))
    for j in jobs:
        s = st[j["id"]]
        if s["status"] in ("failed", "conflict"):
            L.append(f"  {s['status'].upper():8} {j['id']}: {s['reason']}")
    for m, (c, why) in canary.items():
        if c == "held":
            L.append(f"  HELD     {m}: {why}  (fix, then: partc retry {m})")
    return "\n".join(L) + "\n"


def cmd_status(a):
    proto, methods, best_plain, jobs, waiting, st, canary, picks = snapshot()
    live = subprocess.run(["pgrep", "-af", "python -m rq1kit"], capture_output=True, text=True).stdout
    running = {j["id"] for j in jobs if st[j["id"]]["status"] != "done"
               and re.search(re.escape(f"--run_dir {j['run_dir']}") + r"(\s|$)", live, re.M)}
    st = derive(jobs, read_state(), running_ids=running)
    print(render_status(proto, methods, jobs, waiting, st, canary, picks, legacy_queue_running()), end="")


def cmd_plan(a):
    proto, methods, best_plain, jobs, waiting, st, canary, picks = snapshot()
    c = Counter(s["status"] for s in st.values())
    print(f"{len(jobs)} jobs written down now: " + ", ".join(f"{k} {v}" for k, v in sorted(c.items())))
    print(f"{sum(n for *_, n in waiting)} final jobs will be added as picks are made ({len(waiting)} method x dataset)")
    missing = [f"{ds}|{proto['tune']['model']}|{m['loss']}" for m in methods for ds in m["datasets"]
               if f"{ds}|{proto['tune']['model']}|{m['loss']}" not in best_plain]
    if missing:
        print("NOT PLANNED, plain settings missing for:", ", ".join(sorted(set(missing))))
    for j, need in runnable(proto, jobs, st, canary)[: a.n]:
        print(f"next: {j['id']} (slots {need})\n      {j['cmd']}")


def cmd_show(a):
    proto, methods, best_plain, jobs, waiting, st, canary, picks = snapshot()
    m = next((m for m in methods if a.name in (m["name"], m["display"])), None)
    if m:
        print(json.dumps(m, indent=2))
        print("canary:", *canary[m["name"]])
        print("picks:", json.dumps(picks.get(m["name"], {}), indent=2))
        for ds in m["datasets"]:
            c = Counter(st[j["id"]]["status"] for j in jobs if j["method"] == m["name"] and j["dataset"] == ds)
            print(f"  {ds:12} " + ", ".join(f"{k} {v}" for k, v in sorted(c.items())))
        return
    j = next((j for j in jobs if j["id"] == a.name), None)
    if j is None:
        sys.exit(f"no method or job called {a.name}")
    print(json.dumps({k: v for k, v in j.items() if k != "tags"}, indent=2))
    print("status:", st[j["id"]])
    for r in read_state():
        if r["job"] == j["id"]:
            print("  state:", json.dumps(r))
    rj = load_json(os.path.join(j["run_dir"], "run.json"))
    if rj:
        print("run.json:", {k: rj.get(k) for k in ("best_valid_ndcg@20", "best_epoch", "epochs_run", "train_seconds", "peak_gpu_mb")})
    if j["stage"] == "final" and os.path.exists(j["output"]):
        r = load_json(j["output"])
        print("result:", {k: r.get(k) for k in ("ndcg@20", "recall@20", "seen_item_leak_rate", "n_eval_users")})
    print("log tail:\n" + tail(os.path.join(JOBLOGS, f"{j['id']}.log"), 20))


def cmd_retry(a):
    proto, methods, best_plain, jobs, waiting, st, canary, picks = snapshot()
    sel = [j for j in jobs if a.name in (j["id"], j["method"])]
    n = 0
    for j in sel:
        if st[j["id"]]["status"] in ("failed", "conflict", "retry"):
            append_state(dict(job=j["id"], hash=j["hash"], event="reset", reason="partc retry"))
            n += 1
    print(f"reset {n} job(s); the driver picks them up on its next loop")


def cmd_collect(a):
    subprocess.run([sys.executable, "-m", "rq1kit.collect", "--results", "results", "--out", "tables"], check=False)


# ----------------------------------------------------------------------------------------------- check / install
def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_check(a):
    proto, methods = load_protocol(), load_methods()
    problems, notes = [], []
    import importlib
    env = {"python": sys.version.split()[0]}
    for mod in ("torch", "numpy", "scipy", "pandas"):
        try:
            env[mod] = importlib.import_module(mod).__version__
        except Exception as e:  # noqa
            problems.append(f"cannot import {mod}: {e}")
    lock = load_json(ENV_LOCK)
    if a.write_lock or lock is None:
        json.dump(env, open(ENV_LOCK, "w"), indent=2)
        notes.append(f"environment lock written: {env}")
    elif lock != env:
        problems.append(f"environment differs from {ENV_LOCK}: now {env}, locked {lock}")
    files = []
    for ds in proto["datasets"]:
        files += [f"data/{ds}/{f}" for f in ("meta.json", "train.tsv", "valid_clean.tsv", "valid_noisy.tsv", "test.tsv")]
        files += [f"data/{ds}/" + c["train_file"].format(seed=s) for c in proto["conditions"] for s in proto["seeds"]]
    files = sorted(set(files))
    miss = [f for f in files if not os.path.exists(f)]
    if miss:
        problems.append("data files missing: " + ", ".join(miss[:6]) + (" ..." if len(miss) > 6 else ""))
    dl = load_json(DATA_LOCK)
    if not miss:
        sums = {f: md5(f) for f in files}
        if a.write_lock or dl is None:
            json.dump(sums, open(DATA_LOCK, "w"), indent=2, sort_keys=True)
            notes.append(f"data lock written for {len(sums)} files")
        else:
            changed = [f for f in files if dl.get(f) != sums[f]]
            if changed:
                problems.append("data files changed since the lock: " + ", ".join(changed[:6]))
    bp = load_json(BEST_PLAIN, {})
    need = {f"{ds}|{c['model']}|{m['loss']}" for m in methods for ds in m["datasets"] for c in proto["conditions"]
            if c["model"] in m["backbones"]} | {f"{ds}|{proto['tune']['model']}|{m['loss']}" for m in methods for ds in m["datasets"]}
    lack = sorted(k for k in need if k not in bp)
    if lack:
        problems.append("plain settings missing in configs/best_plain.json: " + ", ".join(lack))
    for m in methods:
        g = m["grid"]
        if len(g) > proto["tune"]["max_trials"]:
            notes.append(f"{m['name']}: grid has {len(g)} points, only the first {proto['tune']['max_trials']} are tuned")
        if any(set(p) != set(g[0]) for p in g):
            problems.append(f"{m['name']}: grid points do not all set the same parameters")
        for k in ("source", "grid_source", "backbones", "datasets", "memory"):
            if not m.get(k):
                problems.append(f"{m['name']}: config lacks '{k}'")
    free_gb = shutil.disk_usage(".").free / 2 ** 30
    min_gb = proto.get("min_free_disk_gb", 20)
    (problems if free_gb < min_gb else notes).append(f"disk free: {free_gb:.0f} GB (need {min_gb})")
    notes.append(f"GPU: {gpu_line()}")
    lq = legacy_queue_running()
    if lq:
        notes.append(f"rq1kit.queue running (pids {' '.join(lq)}): the driver will wait for it")
    for n in notes:
        print("  note:", n)
    for p in problems:
        print("  PROBLEM:", p)
    print("check: OK" if not problems else f"check: {len(problems)} problem(s)")
    sys.exit(1 if problems else 0)


def cmd_install(a):
    base = os.environ.get("CONDA_EXE", "")
    base = os.path.dirname(os.path.dirname(base)) if base else os.path.expanduser("~/miniconda3")
    envname = os.environ.get("CONDA_DEFAULT_ENV", "rq1")
    unit_dir = os.path.expanduser("~/.config/systemd/user")
    os.makedirs(unit_dir, exist_ok=True)
    unit = f"""[Unit]
Description=Part C pipeline (python -m rq1kit.partc run)

[Service]
Type=simple
WorkingDirectory={os.getcwd()}
ExecStart=/bin/bash -c 'source {base}/etc/profile.d/conda.sh && conda activate {envname} && exec python -u -m rq1kit.partc run'
Restart=on-failure
RestartSec=60
KillMode=control-group
StandardOutput=append:{os.path.join(os.getcwd(), LOGDIR, 'driver.log')}
StandardError=append:{os.path.join(os.getcwd(), LOGDIR, 'driver.log')}

[Install]
WantedBy=default.target
"""
    os.makedirs(LOGDIR, exist_ok=True)
    path = os.path.join(unit_dir, "partc.service")
    with open(path, "w") as f:
        f.write(unit)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    subprocess.run(["systemctl", "--user", "enable", "partc"], check=False)
    print(f"wrote {path} (conda {base}, env {envname}); enabled. Start it with: systemctl --user start partc")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check"); p.add_argument("--write-lock", action="store_true"); p.set_defaults(f=cmd_check)
    p = sub.add_parser("plan"); p.add_argument("-n", type=int, default=5); p.set_defaults(f=cmd_plan)
    p = sub.add_parser("run"); p.add_argument("--until-idle", action="store_true"); p.add_argument("--poll", type=float, default=10)
    p.set_defaults(f=cmd_run)
    sub.add_parser("status").set_defaults(f=cmd_status)
    p = sub.add_parser("show"); p.add_argument("name"); p.set_defaults(f=cmd_show)
    p = sub.add_parser("retry"); p.add_argument("name"); p.set_defaults(f=cmd_retry)
    sub.add_parser("collect").set_defaults(f=cmd_collect)
    sub.add_parser("install").set_defaults(f=cmd_install)
    a = ap.parse_args()
    if not os.path.exists(PROTOCOL):
        sys.exit(f"run from the kit folder (needs {PROTOCOL}); cd ~/rq1-kit")
    a.f(a)


if __name__ == "__main__":
    main()
