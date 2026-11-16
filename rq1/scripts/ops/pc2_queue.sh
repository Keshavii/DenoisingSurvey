#!/bin/bash
# PC2 (anurag@home) unattended queue. Run by the systemd user service survey-queue (install: scripts/ops/install.sh pc2);
# after a reboot or an error the service starts it again and every step skips what is already done.
#   1. RQ4 ML-1M: tuning, picks and all 831 finals (R4 and R5 need the Llama files that only PC2 has).
#   (Yelp is entirely on PC3 since 13 Nov.) Every job has a time limit (rq4_run.sh: 4 h tuning, 12 h finals).
#   2. RQ10 noise seed 2 for the sequential specialists (16 Nov): builds the envs fmlp, steam, recbole, takes FMLP's Sports
#      and Yelp files from PC3, then stage 2 (27 runs, about 30 h). Log ~/rq10_seeds.log.
set -u
REPO=${REPO:-$HOME/survey}
KIT=$REPO/rq1
WAIT=${WAIT:-1200}
export GIT_TERMINAL_PROMPT=0
say() { echo "$(date '+%F %T') [pc2-queue] $*"; }
say "start, code $(git -C "$REPO" log -1 --format=%h 2>/dev/null)"

DATASETS=ml1m bash "$KIT/scripts/rq4_run.sh" || { say "RQ4 ML-1M stopped with an error (see above); the service will retry"; exit 1; }

# Yelp seed 2 moved to PC3 on 13 Nov (PC3 has the Yelp picks and the same files; PC2 had been stuck since 6 Nov).
say "RQ4 ML-1M finished"

# RQ10 seed 2: PC3 (peer) is read from ~/.survey_relay ("pc3 aura1@host"), the file the status relay uses
PEER=$(awk '$1=="pc3"{print $2}' "$HOME/.survey_relay" 2>/dev/null | head -1)
say "RQ10 noise seed 2 (log ~/rq10_seeds.log, peer ${PEER:-none})"
bash "$KIT/scripts/rq10/rq10_seed_run.sh" 2 "$PEER" >> "$HOME/rq10_seeds.log" 2>&1 \
  || { say "RQ10 seed 2 stopped with an error (last lines of ~/rq10_seeds.log: $(tail -2 "$HOME/rq10_seeds.log" | tr '\n' ' ' | cut -c1-200)); the service will retry"; exit 1; }
say "PC2 queue complete: RQ4 ML-1M and RQ10 seed 2 finished"
