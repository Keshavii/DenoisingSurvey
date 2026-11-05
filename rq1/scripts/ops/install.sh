#!/bin/bash
# Sets up this PC for unattended running. Safe to run again (it rewrites the same unit files).
#   bash ~/survey/rq1/scripts/ops/install.sh
# All PCs: timer survey-snapshot (every 30 min: status + results to the GitHub branch "status").
# PC2, PC3: service survey-queue (pc2_queue.sh / pc3_queue.sh), started at boot, restarted after an error.
#   PC2: the old transient unit rq4run is stopped first (its queue resumes inside survey-queue; at most the 4 trials
#        running at that moment start again).
#   PC3: the running unit rq10rerun is left alone; survey-queue waits for it.
# PC1: nothing is started or stopped; partc.service stays as it is.
set -eu
case "$(whoami)" in aura3) PC=pc1 ;; anurag) PC=pc2 ;; aura1) PC=pc3 ;; *) echo "unknown user $(whoami)"; exit 1 ;; esac
OPS=$HOME/survey/rq1/scripts/ops
UD=$HOME/.config/systemd/user
mkdir -p "$UD"
say() { echo "[$PC] $*"; }

cat > "$UD/survey-snapshot.service" <<EOF
[Unit]
Description=Survey status and results to GitHub (branch status)

[Service]
Type=oneshot
ExecStart=/bin/bash $OPS/snapshot.sh
Nice=19
IOSchedulingClass=idle
TimeoutStartSec=900
EOF
cat > "$UD/survey-snapshot.timer" <<EOF
[Unit]
Description=Survey snapshot every 30 min

[Timer]
OnBootSec=10min
OnUnitActiveSec=30min

[Install]
WantedBy=timers.target
EOF

if [ "$PC" != pc1 ]; then
  cat > "$UD/survey-queue.service" <<EOF
[Unit]
Description=Survey unattended queue ($PC)
StartLimitIntervalSec=86400
StartLimitBurst=6

[Service]
Type=simple
ExecStart=/bin/bash $OPS/${PC}_queue.sh
Restart=on-failure
RestartSec=600
KillMode=control-group
TimeoutStopSec=60
StandardOutput=append:$HOME/survey_queue.log
StandardError=append:$HOME/survey_queue.log

[Install]
WantedBy=default.target
EOF
fi
systemctl --user daemon-reload
systemctl --user enable --now survey-snapshot.timer
say "timer survey-snapshot: $(systemctl --user is-active survey-snapshot.timer)"

if [ "$PC" = pc2 ]; then
  if systemctl --user is-active --quiet rq4run; then
    systemctl --user stop rq4run && say "stopped old unit rq4run"
    sleep 5
    if pgrep -f 'rq1kit\.(queue|rq4)' > /dev/null; then say "WARNING: RQ4 processes still running, not starting:"; pgrep -af 'rq1kit\.(queue|rq4)'; exit 1; fi
  fi
fi
if [ "$PC" != pc1 ]; then
  systemctl --user enable survey-queue
  systemctl --user start survey-queue
  sleep 3
  say "service survey-queue: $(systemctl --user is-active survey-queue) (log ~/survey_queue.log)"
else
  say "partc.service: $(systemctl --user is-enabled partc 2>/dev/null) / $(systemctl --user is-active partc)"
fi
[ "$(loginctl show-user "$(whoami)" -p Linger --value 2>/dev/null)" = yes ] && say "linger: yes" \
  || say "WARNING linger is off: services stop at logout. Fix: sudo loginctl enable-linger $(whoami)"

say "first snapshot (can take a minute)..."
bash "$OPS/snapshot.sh" || true
tail -1 "$HOME/survey_snapshot.log"
