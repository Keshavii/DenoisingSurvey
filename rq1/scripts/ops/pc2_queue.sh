#!/bin/bash
# PC2 (anurag@home) unattended queue. Run by the systemd user service survey-queue (install: scripts/ops/install.sh pc2);
# after a reboot or an error the service starts it again and every step skips what is already done.
#   1. RQ4 ML-1M: tuning, picks and all 831 finals (R4 and R5 need the Llama files that only PC2 has).
#   2. RQ4 Yelp finals of seed 2, from the Yelp picks that PC3 publishes on the GitHub branch "status"
#      (PC3 tunes Yelp and runs seed 1, so the two PCs share Yelp's 338 finals).
set -u
REPO=${REPO:-$HOME/survey}
KIT=$REPO/rq1
WAIT=${WAIT:-1200}
say() { echo "$(date '+%F %T') [pc2-queue] $*"; }
say "start, code $(git -C "$REPO" log -1 --format=%h 2>/dev/null)"

DATASETS=ml1m bash "$KIT/scripts/rq4_run.sh" || { say "RQ4 ML-1M stopped with an error (see above); the service will retry"; exit 1; }

P=$KIT/configs/rq4/picks_yelp_from_pc3.json
until [ -s "$P" ]; do
  if git -C "$REPO" fetch -q origin status 2>/dev/null \
     && git -C "$REPO" show origin/status:pc3/rq1/configs/rq4/picks_yelp.json > "$P.tmp" 2>/dev/null && [ -s "$P.tmp" ]; then
    mv "$P.tmp" "$P"; say "got PC3's Yelp picks"; break
  fi
  rm -f "$P.tmp"
  say "waiting for PC3's Yelp picks (pc3/rq1/configs/rq4/picks_yelp.json on branch status); next look in $((WAIT / 60)) min"
  sleep "$WAIT"
done

DATASETS=yelp TUNE=0 PICKS_FROM="$P" FINAL_SEEDS=2 bash "$KIT/scripts/rq4_run.sh" \
  || { say "RQ4 Yelp seed 2 stopped with an error (see above); the service will retry"; exit 1; }
say "PC2 queue complete: nothing left to run"
