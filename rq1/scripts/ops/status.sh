#!/bin/bash
# One-screen status of whichever PC this runs on (PC1 aura3, PC2 anurag, PC3 aura1). Read-only: starts nothing.
#   bash ~/survey/rq1/scripts/ops/status.sh          # short, for the terminal
#   bash ~/survey/rq1/scripts/ops/status.sh --full   # longer, used by the GitHub status snapshot
# Lines starting with ALERT need a look.
set +e
FULL=0; [ "${1:-}" = "--full" ] && FULL=1
case "$(whoami)" in
  aura3) PC=pc1 ;; anurag) PC=pc2 ;; aura1) PC=pc3 ;; *) PC="$(whoami)" ;;
esac
REPO=$HOME/survey
KIT=$REPO/rq1; [ "$PC" = pc1 ] && [ -d "$HOME/rq1-kit" ] && KIT=$HOME/rq1-kit
hr() { echo "---- $* ----"; }

echo "$PC ($(whoami)@$(hostname))  $(date '+%F %T %Z')  up since $(uptime -s 2>/dev/null)"
echo "code $(git -C "$REPO" log -1 --format='%h %cd' --date=format:'%d %b %H:%M' 2>/dev/null)  linger $(loginctl show-user "$(whoami)" -p Linger --value 2>/dev/null)  disk free $(df -h --output=avail "$HOME" | tail -1 | tr -d ' ')  $(free -g | awk '/^Mem/{print "ram used "$3"/"$2" GB"} /^Swap/{print "swap "$3" GB"}' | tr '\n' ' ')"
echo "gpu $(nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader 2>/dev/null)"
hr "services"
systemctl --user list-units --type=service --all --no-legend --plain 2>/dev/null \
  | grep -E 'partc|rq4|rq10|llard|survey' | awk '{printf "  %-28s %s %s\n", $1, $3, $4}'
for u in survey-queue partc; do
  systemctl --user cat "$u" > /dev/null 2>&1 || continue
  [ "$(systemctl --user is-active "$u")" = failed ] && echo "ALERT: $u has failed: journalctl --user -u $u -n 30"
  [ "$(systemctl --user is-enabled "$u" 2>/dev/null)" = enabled ] || echo "ALERT: $u is not enabled (will not start after a reboot)"
done
if [ "$PC" != pc1 ] && ! systemctl --user cat survey-queue > /dev/null 2>&1; then echo "  (survey-queue not installed yet)"; fi
[ -s "$HOME/survey_snapshot.log" ] && echo "  last snapshot: $(tail -1 "$HOME/survey_snapshot.log")"
tail -1 "$HOME/survey_snapshot.log" 2>/dev/null | grep -q FAILED && echo "ALERT: GitHub snapshot is failing (see ~/survey_snapshot.log)"
tail -4 "$HOME/survey_snapshot.log" 2>/dev/null | grep -q "relay .*FAILED" && echo "ALERT: could not fetch another PC's status over SSH (see ~/survey_snapshot.log)"
hr "gpu jobs"
ps -eo pid,etime,args --no-headers 2>/dev/null | grep -E 'rq1kit\.(rq4|backbone|partc run|adt|sgl|bod|deca|dcf|pld|diffrec|ddrm|rgcf|llard|drrl|noise)|main\.py|run_GBSR|run_HDSR|gdmsr|run_hsd|run_ssdrec|run_fmlp|vllm' \
  | grep -v grep | grep -v 'partc status' | awk '{a=""; for(i=3;i<=NF;i++) a=a" "$i; printf "  %-11s%s\n", $2, substr(a,1,120)}' | head -12

# --- queue progress for rq1kit.queue folders (RQ4) ---
queue_progress() {  # queue_progress <jobs.csv[:jobs2.csv...]> <logdir> <label>
  python3 - "$1" "$2" "$3" <<'EOF'
import csv, json, os, statistics, sys, time
paths, logdir, label = sys.argv[1].split(":"), sys.argv[2], sys.argv[3]
paths = [p for p in paths if os.path.isfile(p)]
if not paths:
    print(f"  {label}: not started"); sys.exit()
jobs = {}
for p in paths:
    for j in csv.DictReader(open(p)):
        jobs[j["job_id"]] = j
jobs = list(jobs.values())
state = os.path.join(logdir, "state.jsonl")
last = {}
for line in (open(state) if os.path.isfile(state) else []):
    try:
        r = json.loads(line); last[r["job_id"]] = r
    except Exception:
        pass
meds = []
for ds in sorted({j["job_id"].split("_")[1] for j in jobs}):
    js = [j for j in jobs if j["job_id"].split("_")[1] == ds]
    ok = [last[j["job_id"]] for j in js if j["job_id"] in last and last[j["job_id"]]["status"] == "ok"]
    bad = [last[j["job_id"]] for j in js if j["job_id"] in last and last[j["job_id"]]["status"] != "ok"]
    left = len(js) - len(ok)
    par = max(1, 4 // int(js[0].get("slots") or 1))
    eta = ""
    if ok:
        med = statistics.median(r["seconds"] for r in ok)
        meds.append(med)
        if left:
            eta = f", median {med/60:.0f} min/job, ~{left*med/par/3600:.0f} h left at {par} in parallel"
    print(f"  {label} {ds}: {len(ok)}/{len(js)} done, {len(bad)} failed so far{eta}")
    for r in bad[-3:]:
        log = os.path.join(logdir, r["job_id"] + ".log")
        tail = open(log, errors="replace").read().strip().splitlines()[-1:] if os.path.isfile(log) else ["(no log)"]
        print(f"    failed {r['job_id']} ({r['status']}): {tail[0][:110] if tail else ''}")
if os.path.isfile(state) and any(j["job_id"] not in last or last[j["job_id"]]["status"] != "ok" for j in jobs):
    idle = time.time() - os.path.getmtime(state)
    limit = max(3 * max(meds or [3600]), 3 * 3600)
    if idle > limit and os.system("pgrep -f 'rq1kit.queue' > /dev/null") == 0:
        print(f"ALERT: {label}: no job has finished for {idle/3600:.1f} h (limit {limit/3600:.1f} h); a job may be stuck")
EOF
}

case "$PC" in
pc1)
  hr "RQ1 Part C (partc driver status, refreshed every minute)"
  S=$KIT/logs/partc/status.txt
  if [ -f "$S" ]; then
    age=$(( $(date +%s) - $(date -r "$S" +%s) ))
    echo "  status file written $(date -r "$S" '+%F %T')"
    [ $age -gt 900 ] && systemctl --user is-active --quiet partc && echo "ALERT: partc driver has not refreshed its status for $((age / 60)) min"
    if [ $FULL = 1 ]; then cat "$S"; else
      grep -E '^(total:|rough finish)' "$S" | sed 's/^/  /'
      echo "  failed/held: $(grep -cE '^  (FAILED|CONFLICT|HELD)' "$S")"; grep -E '^  (FAILED|CONFLICT|HELD)' "$S" | cut -c1-130 | head -6
    fi
  else echo "  no $S"; fi
  ;;
pc2|pc3)
  hr "RQ4 (signal x treatment)"
  C=$KIT/configs/rq4
  T=$C/jobs_tune_here.csv; [ -f "$T" ] || T=$C/jobs_tune.csv
  F=$(ls "$C"/jobs_final_*.csv 2>/dev/null | tr '\n' ':'); [ -n "$F" ] || F=$C/jobs_final.csv
  queue_progress "$T" "$KIT/logs/rq4_tune" tune
  for p in "$C"/picks_*.json; do [ -f "$p" ] && echo "  picks: $(basename "$p") ($(python3 -c "import json;print(len(json.load(open('$p'))))") cells)"; done
  queue_progress "$F" "$KIT/logs/rq4_final" final
  for d in "$C"/done_*; do [ -f "$d" ] && echo "  finished: ${d##*/done_}"; done
  ;;
esac
if [ "$PC" = pc3 ]; then
  hr "RQ10 (specialists)"
  R10=$HOME/survey/rq10
  echo "  .done markers: $(find "$R10/logs" -maxdepth 1 -name '*.done' 2>/dev/null | wc -l)  ($(find "$R10/logs" -maxdepth 1 -name '*.done' -printf '%f ' 2>/dev/null | sed 's/run_//g;s/\.done//g'))"
  [ -s "$HOME/rq10_rerun.log" ] && { echo "  last lines of ~/rq10_rerun.log:"; tail -3 "$HOME/rq10_rerun.log" | cut -c1-140 | sed 's/^/    /'; }
  if [ $FULL = 1 ] && [ -f "$R10/results/run_summary.tsv" ]; then
    echo "  run_summary.tsv (name, exit code, minutes, peak MiB):"; sed 's/^/    /' "$R10/results/run_summary.tsv"
  fi
fi
if [ -s "$HOME/survey_queue.log" ]; then
  hr "queue log (~/survey_queue.log)"
  N=4; [ $FULL = 1 ] && N=15
  grep -vE "^\{'job_id'" "$HOME/survey_queue.log" | tail -"$N" | cut -c1-160 | sed 's/^/  /'
fi
if [ $FULL = 1 ]; then
  hr "recent service log lines"
  journalctl --user --since "-2h" --no-pager -o short-iso 2>/dev/null | grep -E 'survey|rq4|rq10|partc' | tail -8
fi
