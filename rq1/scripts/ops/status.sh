#!/bin/bash
# One-screen status of whichever PC this runs on (PC1 aura3, PC2 anurag, PC3 aura1). Read-only: starts nothing.
#   bash ~/survey/rq1/scripts/ops/status.sh          # short, for the terminal
#   bash ~/survey/rq1/scripts/ops/status.sh --full   # longer, used by the GitHub status snapshot
set +e
FULL=0; [ "${1:-}" = "--full" ] && FULL=1
case "$(whoami)" in
  aura3) PC=pc1 ;; anurag) PC=pc2 ;; aura1) PC=pc3 ;; *) PC="$(whoami)" ;;
esac
REPO=$HOME/survey
KIT=$REPO/rq1; [ "$PC" = pc1 ] && [ -d "$HOME/rq1-kit" ] && KIT=$HOME/rq1-kit
hr() { echo "---- $* ----"; }

echo "$PC ($(whoami)@$(hostname))  $(date '+%F %T %Z')  up since $(uptime -s 2>/dev/null)"
echo "code $(git -C "$REPO" log -1 --format='%h %cd' --date=format:'%d %b %H:%M' 2>/dev/null)  linger $(loginctl show-user "$(whoami)" -p Linger --value 2>/dev/null)  disk free $(df -h --output=avail "$HOME" | tail -1 | tr -d ' ')"
echo "gpu $(nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader 2>/dev/null)"
hr "services"
systemctl --user list-units --type=service --all --no-legend --plain 2>/dev/null \
  | grep -E 'partc|rq4|rq10|llard|survey' | awk '{printf "  %-28s %s %s\n", $1, $3, $4}'
systemctl --user list-timers --all --no-legend 2>/dev/null | grep -E 'survey' | awk '{print "  timer next: "$1" "$2" "$3}'
hr "gpu jobs"
ps -eo pid,etime,args --no-headers 2>/dev/null | grep -E 'rq1kit\.(rq4|backbone|partc run|adt|sgl|bod|deca|dcf|pld|diffrec|ddrm|rgcf|llard|drrl)|main\.py|run_GBSR|run_HDSR|gdmsr|run_hsd|run_ssdrec|run_fmlp|vllm' \
  | grep -v grep | grep -v 'partc status' | awk '{a=""; for(i=3;i<=NF;i++) a=a" "$i; printf "  %-11s%s\n", $2, substr(a,1,120)}' | head -12

# --- queue progress for rq1kit.queue folders (RQ4) ---
queue_progress() {  # queue_progress <jobs.csv> <logdir> <label>
  python3 - "$1" "$2" "$3" <<'EOF'
import csv, json, os, statistics, sys, time
jobs_csv, logdir, label = sys.argv[1:4]
if not os.path.isfile(jobs_csv):
    print(f"  {label}: not started (no {jobs_csv})"); sys.exit()
jobs = list(csv.DictReader(open(jobs_csv)))
state = os.path.join(logdir, "state.jsonl")
last = {}
for line in (open(state) if os.path.isfile(state) else []):
    try:
        r = json.loads(line); last[r["job_id"]] = r
    except Exception:
        pass
for ds in sorted({j["job_id"].split("_")[1] for j in jobs}):
    js = [j for j in jobs if j["job_id"].split("_")[1] == ds]
    ok = [last[j["job_id"]] for j in js if j["job_id"] in last and last[j["job_id"]]["status"] == "ok"]
    bad = [last[j["job_id"]] for j in js if j["job_id"] in last and last[j["job_id"]]["status"] != "ok"]
    left = len(js) - len(ok)
    par = max(1, 4 // int(js[0].get("slots") or 1))
    eta = ""
    if ok and left:
        med = statistics.median(r["seconds"] for r in ok)
        eta = f", median {med/60:.0f} min/job, ~{left*med/par/3600:.0f} h left at {par} in parallel"
    print(f"  {label} {ds}: {len(ok)}/{len(js)} done, {len(bad)} failed{eta}")
    for r in bad[-3:]:
        log = os.path.join(logdir, r["job_id"] + ".log")
        tail = open(log, errors="replace").read().strip().splitlines()[-1:] if os.path.isfile(log) else ["(no log)"]
        print(f"    FAILED {r['job_id']} ({r['status']}): {tail[0][:110] if tail else ''}")
EOF
}

case "$PC" in
pc1)
  hr "RQ1 Part C (partc driver status, refreshed every minute)"
  S=$KIT/logs/partc/status.txt
  if [ -f "$S" ]; then
    echo "  status file written $(date -r "$S" '+%F %T')"
    if [ $FULL = 1 ]; then cat "$S"; else
      grep -E '^(total:|rough finish)' "$S" | sed 's/^/  /'
      echo "  failed/held: $(grep -cE '^  (FAILED|CONFLICT|HELD)' "$S")"; grep -E '^  (FAILED|CONFLICT|HELD)' "$S" | cut -c1-130 | head -6
    fi
  else echo "  no $S"; fi
  ;;
pc2|pc3)
  hr "RQ4 (signal x treatment)"
  queue_progress "$KIT/configs/rq4/jobs_tune.csv" "$KIT/logs/rq4_tune" tune
  [ -f "$KIT/configs/rq4/best.json" ] && echo "  picks: $(python3 -c "import json;print(len(json.load(open('$KIT/configs/rq4/best.json'))))") cells in configs/rq4/best.json"
  queue_progress "$KIT/configs/rq4/jobs_final.csv" "$KIT/logs/rq4_final" final
  for f in "$HOME"/rq4_queue.log "$HOME"/rq4_run.log; do
    [ -s "$f" ] && { echo "  last lines of $f:"; grep -vE "^\{'job_id'" "$f" | tail -3 | sed 's/^/    /'; break; }
  done
  ;;
esac
if [ "$PC" = pc3 ]; then
  hr "RQ10 (specialists)"
  R10=$HOME/survey/rq10
  echo "  .done markers: $(find "$R10/logs" -maxdepth 1 -name '*.done' 2>/dev/null | wc -l)  ($(find "$R10/logs" -maxdepth 1 -name '*.done' -printf '%f ' 2>/dev/null | sed 's/run_//g;s/\.done//g'))"
  for f in "$HOME"/pc3_queue.log "$HOME"/rq10_rerun.log; do
    [ -s "$f" ] && { echo "  last lines of $f:"; tail -4 "$f" | sed 's/^/    /'; break; }
  done
  if [ $FULL = 1 ] && [ -f "$R10/results/run_summary.tsv" ]; then
    echo "  run_summary.tsv (name, exit code, minutes, peak MiB):"; sed 's/^/    /' "$R10/results/run_summary.tsv"
  fi
fi
if [ $FULL = 1 ]; then
  hr "recent service log lines"
  journalctl --user --since "-2h" --no-pager -o short-iso 2>/dev/null | grep -E 'survey|rq4|rq10|partc' | tail -8
fi
