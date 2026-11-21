#!/bin/bash
# PC1 (aura3@home) unattended queue. Run by the systemd user service survey-queue (install: scripts/ops/install.sh);
# after a reboot or an error the service starts it again and every step skips what is already done.
#   1. Wait until RQ1 Part C (partc.service) has nothing left to run: partc-resume has done its restart (RGCF's second
#      canary chance) and three checks 10 min apart show 0 running jobs. Part C keeps priority over RQ2.
#   2. RQ2 (lean): rho* per dataset, MF-BPR on each clean base (for N3), the N1/N2/N3 files at rho*, then about 500
#      runs with the Part C picks (scripts/rq2_jobs.py), a normal queue pass and a pass that reruns failures alone.
# While RQ2's queue runs, partc starts nothing new (configs/partc/scheduler.json: slots_taken_by_legacy_queue 4).
set -u
KIT=${KIT:-$HOME/rq1-kit}
SLOTS=${SLOTS:-4}
WAIT=${WAIT:-600}
cd "$KIT" || exit 1
if [ "${NO_CONDA:-0}" != 1 ]; then
  set +u; source ~/miniconda3/etc/profile.d/conda.sh; conda activate rq1; set -u
fi
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-7} MKL_NUM_THREADS=${MKL_NUM_THREADS:-7}
say() { echo "$(date '+%F %T') [pc1-queue] $*"; }
say "start, code $(git log -1 --format=%h 2>/dev/null)"

if [ ! -f configs/rq2/started ]; then
  idle=0
  while [ $idle -lt 3 ]; do
    if systemctl --user is-active --quiet partc-resume 2>/dev/null; then
      idle=0; why="partc-resume has not restarted partc yet"
    else
      n=$(python -m rq1kit.partc status 2>/dev/null | grep -oE '[0-9]+ running' | head -1 | grep -oE '^[0-9]+')
      if [ "${n:-x}" = 0 ]; then idle=$((idle + 1)); else idle=0; fi
      why="Part C running: ${n:-?}"
    fi
    [ $idle -ge 3 ] && break
    say "waiting for Part C to finish ($why; idle checks $idle/3); next look in $((WAIT / 60)) min"
    sleep "$WAIT"
  done
  say "Part C has nothing left to run: starting RQ2"
  mkdir -p configs/rq2 && date '+%F %T' > configs/rq2/started
fi

git pull -q --ff-only 2>/dev/null || say "note: git pull in $KIT did not run (local changes?); using the code as it is"
[ -f scripts/rq2_jobs.py ] || { say "scripts/rq2_jobs.py missing in $KIT"; exit 1; }
say "RQ2 1/4 rho*"
[ -f configs/rq2/rho.json ] || python scripts/rq2_jobs.py rho || { say "rho failed"; exit 1; }
say "RQ2 2/4 MF-BPR on the clean bases (top-K for N3)"
python scripts/rq2_jobs.py prep | while read -r cmd; do
  say "  $cmd"; $cmd > /dev/null || { say "  FAILED: $cmd"; exit 1; }
done || exit 1
say "RQ2 3/4 noise files"
python scripts/rq2_jobs.py noise || { say "noise files failed"; exit 1; }
say "RQ2 4/4 runs"
python scripts/rq2_jobs.py jobs > configs/rq2/jobs.csv || { say "job list failed"; exit 1; }
python -m rq1kit.queue --jobs configs/rq2/jobs.csv --slots "$SLOTS" --logs logs/rq2
say "  retry pass: failed RQ2 jobs, one at a time"
python -m rq1kit.queue --jobs configs/rq2/jobs.csv --slots 1 --logs logs/rq2
touch configs/rq2/done

# RQ5 (lean): popularity-noise curves 10/30/50% on Yelp and Gowalla, Part C picks, LightGCN, 3 seeds (scripts/rq5_jobs.py
# lives in the survey repo; it runs against this kit through KIT). Every step skips what is already done.
RQ5=$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)/rq5_jobs.py
[ -f "$RQ5" ] || { say "$RQ5 missing (git pull in ~/survey)"; exit 1; }
export KIT
mkdir -p configs/rq5
say "RQ5 1/2 noise files"
python "$RQ5" noise || { say "RQ5 noise files failed"; exit 1; }
say "RQ5 2/2 runs"
python "$RQ5" jobs > configs/rq5/jobs.csv || { say "RQ5 job list failed"; exit 1; }
python -m rq1kit.queue --jobs configs/rq5/jobs.csv --slots "$SLOTS" --logs logs/rq5
say "  retry pass: failed RQ5 jobs, one at a time"
python -m rq1kit.queue --jobs configs/rq5/jobs.csv --slots 1 --logs logs/rq5
touch configs/rq5/done
say "PC1 queue complete: RQ2 and RQ5 finished (results/RQ2, results/RQ5)"
