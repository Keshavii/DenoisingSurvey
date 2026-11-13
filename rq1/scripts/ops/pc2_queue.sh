#!/bin/bash
# PC2 (anurag@home) unattended queue. Run by the systemd user service survey-queue (install: scripts/ops/install.sh pc2);
# after a reboot or an error the service starts it again and every step skips what is already done.
#   1. RQ4 ML-1M: tuning, picks and all 831 finals (R4 and R5 need the Llama files that only PC2 has).
#   (Yelp is entirely on PC3 since 13 Nov.) Every job has a time limit (rq4_run.sh: 4 h tuning, 12 h finals).
set -u
REPO=${REPO:-$HOME/survey}
KIT=$REPO/rq1
WAIT=${WAIT:-1200}
export GIT_TERMINAL_PROMPT=0
say() { echo "$(date '+%F %T') [pc2-queue] $*"; }
say "start, code $(git -C "$REPO" log -1 --format=%h 2>/dev/null)"

DATASETS=ml1m bash "$KIT/scripts/rq4_run.sh" || { say "RQ4 ML-1M stopped with an error (see above); the service will retry"; exit 1; }

# Yelp seed 2 moved to PC3 on 13 Nov (PC3 has the Yelp picks and the same files; PC2 had been stuck since 6 Nov).
say "PC2 queue complete: RQ4 ML-1M finished"
