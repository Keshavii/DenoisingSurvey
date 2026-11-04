#!/bin/bash
# PC1: restart the partc driver as soon as it has nothing running, so a code change (here: the canary rule that
# releases RGCF) takes effect without killing a running job. Idle = "0 running" in two checks INTERVAL apart.
#   systemd-run --user --unit=partc-resume --collect bash -c "bash ~/rq1-kit/scripts/partc_resume_when_idle.sh > ~/partc_resume.log 2>&1"
set -u
KIT=${KIT:-$HOME/rq1-kit}
INTERVAL=${INTERVAL:-300}
UNIT=${UNIT:-partc}
say() { echo "$(date '+%F %T') $*"; }
cd "$KIT"
source ~/miniconda3/etc/profile.d/conda.sh
conda activate rq1
running() { python -m rq1kit.partc status 2>/dev/null | grep -oE '[0-9]+ running' | grep -oE '^[0-9]+'; }
say "waiting until $UNIT has nothing running (checked every $INTERVAL s)"
idle=0
while true; do
  n=$(running)
  if [ "${n:-x}" = "0" ]; then idle=$((idle + 1)); else idle=0; fi
  [ $idle -ge 2 ] && break
  sleep "$INTERVAL"
done
say "idle twice in a row; pulling and restarting $UNIT"
git pull -q --ff-only && say "code at $(git log -1 --format=%h)"
systemctl --user restart "$UNIT" && say "$UNIT restarted"
sleep 60
python -m rq1kit.partc status | tail -6
