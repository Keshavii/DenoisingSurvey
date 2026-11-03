#!/bin/bash
# PC3: start the real RQ10 runs automatically, but only once they exist and are tested.
# Waits for the smoke reproductions (rq10repro) to end, then checks GitHub every 15 minutes (for up to 36 hours) for
# rq1/configs/rq10/READY, which is committed only together with a tested rq1/scripts/rq10_run.sh. When it appears, it
# pulls and runs rq10_run.sh, which only queues methods whose smoke reproduction passed (repro_summary.tsv, exit 0).
#   systemd-run --user --unit=rq10next --collect bash -c "bash ~/survey/rq1/scripts/rq10_next.sh > ~/rq10_next.log 2>&1"
set -u
KIT=${KIT:-$HOME/survey}
TRIES=${TRIES:-144}
say() { echo "$(date '+%F %T') $*"; }
say "waiting for rq10repro to finish"
while systemctl --user is-active --quiet rq10repro; do sleep 60; done
say "smoke reproductions finished"
for i in $(seq 1 $TRIES); do
  git -C "$KIT" pull -q --ff-only 2>&1 | tail -1
  if [ -f "$KIT/rq1/configs/rq10/READY" ] && [ -f "$KIT/rq1/scripts/rq10_run.sh" ]; then
    say "READY found at $(git -C "$KIT" log -1 --format=%h); starting rq10_run.sh"
    exec bash "$KIT/rq1/scripts/rq10_run.sh"
  fi
  [ "$i" -lt "$TRIES" ] && sleep ${POLL:-900}
done
say "no READY after $TRIES checks; nothing started"
