#!/bin/bash
# Sets up this PC for unattended running. Safe to run again (it rewrites the same unit files).
#   bash ~/survey/rq1/scripts/ops/install.sh
# All PCs: timer survey-snapshot (every 30 min: status + results to the GitHub branch "status").
# All PCs: service survey-queue (pc1_queue.sh / pc2_queue.sh / pc3_queue.sh), started at boot, restarted after an error.
#   PC2: the old transient unit rq4run is stopped first (its queue resumes inside survey-queue; at most the 4 trials
#        running at that moment start again).
#   PC3: the running unit rq10rerun is left alone; survey-queue waits for it.
# PC1: partc.service is not touched; survey-queue only waits until Part C has nothing left, then runs RQ2.
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

cat > "$UD/survey-queue.service" <<EOF
[Unit]
Description=Survey unattended queue ($PC)
StartLimitIntervalSec=86400
StartLimitBurst=40

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
# Kick: every 2 h start survey-queue. A running queue is left alone (start does nothing); a queue that has finished or
# stopped runs again, and every step skips what is done, so work added by a git pull starts without anyone logging in
# (11-13 Nov: PC3 sat idle two days after its queue completed; PC2 the same on 16 Nov).
cat > "$UD/survey-kick.service" <<EOF
[Unit]
Description=Start survey-queue if it is not running

[Service]
Type=oneshot
ExecStart=/bin/systemctl --user start --no-block survey-queue
EOF
cat > "$UD/survey-kick.timer" <<EOF
[Unit]
Description=Start survey-queue if idle, every 2 h

[Timer]
OnBootSec=30min
OnUnitActiveSec=2h

[Install]
WantedBy=timers.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now survey-snapshot.timer
systemctl --user enable --now survey-kick.timer
say "timer survey-snapshot: $(systemctl --user is-active survey-snapshot.timer); timer survey-kick: $(systemctl --user is-active survey-kick.timer)"

if [ "$PC" = pc2 ]; then
  if systemctl --user is-active --quiet rq4run; then
    systemctl --user stop rq4run && say "stopped old unit rq4run"
    sleep 5
    if pgrep -f 'rq1kit\.(queue|rq4)' > /dev/null; then say "WARNING: RQ4 processes still running, not starting:"; pgrep -af 'rq1kit\.(queue|rq4)'; exit 1; fi
  fi
fi
systemctl --user enable survey-queue
systemctl --user start survey-queue
sleep 3
say "service survey-queue: $(systemctl --user is-active survey-queue) (log ~/survey_queue.log)"
[ "$PC" = pc1 ] && say "partc.service: $(systemctl --user is-enabled partc 2>/dev/null) / $(systemctl --user is-active partc)"
[ "$(loginctl show-user "$(whoami)" -p Linger --value 2>/dev/null)" = yes ] && say "linger: yes" \
  || say "WARNING linger is off: services stop at logout. Fix: sudo loginctl enable-linger $(whoami)"

say "first snapshot (can take a minute)..."
bash "$OPS/snapshot.sh" || true
tail -1 "$HOME/survey_snapshot.log"
