#!/bin/bash
# PC3 (aura1@aura-node1) unattended queue. Run by the systemd user service survey-queue (install: scripts/ops/install.sh pc3);
# after a reboot or an error the service starts it again and every step skips what is already done.
#   1. RQ10 re-runs of 5 Nov (scripts/rq10/rq10_rerun_failed.sh): wait for the running copy (unit rq10rerun), or, if it
#      was cut off (reboot), finish it here; its jobs keep their .done markers, so nothing finished runs twice.
#   2. RQ4 Yelp: tuning (249 trials) and picks (PC2 reads them for its Yelp seed-2 finals).
#   3. RQ10 stage 1 (fixed reproduction runs) and stage 2 (design noise, full-ranking scores): rq10_stage1.sh.
#   4. RQ4 Yelp finals of seed 1.
set -u
REPO=${REPO:-$HOME/survey}
KIT=$REPO/rq1
WAIT=${WAIT:-600}
say() { echo "$(date '+%F %T') [pc3-queue] $*"; }
say "start, code $(git -C "$REPO" log -1 --format=%h 2>/dev/null)"

while systemctl --user is-active --quiet rq10rerun 2>/dev/null; do
  say "RQ10 re-runs still running (unit rq10rerun); next look in $((WAIT / 60)) min"
  sleep "$WAIT"
done
if ! grep -q "rq10_rerun_failed complete" "$HOME/rq10_rerun.log" 2>/dev/null; then
  say "RQ10 re-runs were cut off: finishing them (jobs with a .done marker are skipped)"
  bash "$KIT/scripts/rq10/rq10_rerun_failed.sh" >> "$HOME/rq10_rerun.log" 2>&1
fi
say "RQ10 re-runs complete"

# PC3 has no copy of the kit's datasets: Yelp (with PC2's noise files and reference models) is copied from PC2 once.
until [ -f "$KIT/data/yelp/train.tsv" ] && [ -f "$KIT/data/yelp/train_N3_20_s1.tsv" ]; do
  say "waiting for data/yelp from PC2 (see scripts/ops/README.md); next look in $((WAIT / 60)) min"
  sleep "$WAIT"
done

# Yelp tuning and picks first: PC2 waits for these picks to run Yelp seed 2
DATASETS=yelp STOP_AFTER_PICKS=1 bash "$KIT/scripts/rq4_run.sh" || { say "RQ4 Yelp tuning stopped with an error (see above); the service will retry"; exit 1; }

# RQ10 stage 1 (fixed reproduction runs), one job at a time, alone on the GPU
if ! grep -q "stage 1 complete" "$HOME/rq10_stage1.log" 2>/dev/null; then
  say "RQ10 stage 1 (log ~/rq10_stage1.log)"
  bash "$KIT/scripts/rq10/rq10_stage1.sh" >> "$HOME/rq10_stage1.log" 2>&1
fi

DATASETS=yelp FINAL_SEEDS=1 bash "$KIT/scripts/rq4_run.sh" || { say "RQ4 Yelp finals stopped with an error (see above); the service will retry"; exit 1; }
say "PC3 queue complete: nothing left to run"
