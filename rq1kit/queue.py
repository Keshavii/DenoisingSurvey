"""A resumable job queue for one GPU.

jobs.csv columns: job_id, cwd, cmd, slots   (slots = how many of --slots the job needs; 1 for small jobs)
Each job's stdout/stderr goes to logs/<job_id>.log; its status, wall time and peak GPU memory to
logs/state.jsonl. Finished jobs are skipped on restart, so you can stop and resume at any time.

  python -m rq1kit.queue --jobs configs/rq1_partC_jobs.csv --slots 2

With --slots 2, two 1-slot jobs (e.g. Adressa or MovieLens runs) share the GPU; a 2-slot job runs alone.
"""
import argparse
import csv
import json
import os
import shlex
import subprocess
import threading
import time


def gpu_mem_used_mb():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout
        return int(out.strip().splitlines()[0])
    except Exception:
        return -1


def load_done(state_path):
    done = set()
    if os.path.exists(state_path):
        for line in open(state_path):
            r = json.loads(line)
            if r.get("status") == "ok":
                done.add(r["job_id"])
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--slots", type=int, default=1)
    ap.add_argument("--logs", default="logs")
    ap.add_argument("--only", default="", help="substring filter on job_id")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.logs, exist_ok=True)
    state = os.path.join(a.logs, "state.jsonl")
    done = load_done(state)
    jobs = [j for j in csv.DictReader(open(a.jobs)) if j["job_id"] not in done and a.only in j["job_id"]]
    print(f"{len(jobs)} jobs to run, {len(done)} already done")
    if a.dry:
        for j in jobs[:20]:
            print(j["job_id"], "|", j["cmd"])
        return
    lock = threading.Lock()
    free = [a.slots]
    peak = {"mb": 0}
    stop = threading.Event()

    def watch():
        while not stop.is_set():
            m = gpu_mem_used_mb()
            peak["mb"] = max(peak["mb"], m)
            time.sleep(2)

    def run(job):
        need = int(job.get("slots") or 1)
        t0 = time.time()
        peak["mb"] = 0
        log = open(os.path.join(a.logs, f"{job['job_id']}.log"), "w")
        try:
            p = subprocess.run(shlex.split(job["cmd"]), cwd=job["cwd"] or None, stdout=log, stderr=subprocess.STDOUT)
            status = "ok" if p.returncode == 0 else f"exit {p.returncode}"
        except Exception as e:  # noqa
            status = f"error {e}"
        rec = {"job_id": job["job_id"], "status": status, "seconds": round(time.time() - t0, 1),
               "peak_gpu_mb_while_running": peak["mb"], "slots": need, "finished": time.strftime("%Y-%m-%d %H:%M:%S")}
        with lock:
            open(state, "a").write(json.dumps(rec) + "\n")
            free[0] += need
        print(rec)

    threading.Thread(target=watch, daemon=True).start()
    threads = []
    for job in jobs:
        need = min(int(job.get("slots") or 1), a.slots)
        while True:
            with lock:
                if free[0] >= need:
                    free[0] -= need
                    break
            time.sleep(1)
        t = threading.Thread(target=run, args=(job,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    stop.set()


if __name__ == "__main__":
    main()
