#!/bin/bash
# RQ10 data preparation on PC3: creates N0/N2_20/N3_30 noise variants of each
# sequential dataset in both STEAM and RecBole-atomic formats.
# Social datasets (GBSR/GDMSR/HDSR) use the repos' own data + GBSR's
# fake-tie procedure (noise built into run args: --beta/--sigma).
#
# Output: ~/survey/rq10/data/<Dataset>_<Level>/  (STEAM format)
#         ~/survey/rq10/data/recbole/<Dataset>_<Level>/  (RecBole atomic format)
#
# Run:
#   bash ~/survey/rq1/scripts/rq10/rq10_data_prep.sh
# or unattended:
#   systemd-run --user --unit=rq10data --collect \
#     bash -c "bash ~/survey/rq1/scripts/rq10/rq10_data_prep.sh > ~/rq10_data_prep.log 2>&1"
set -u
ROOT=${ROOT:-$HOME/survey/rq10}
SCRIPTS=$HOME/survey/rq1/scripts/rq10
STEAM_SRC=$ROOT/repos/steam    # ships Beauty/, Sports/, Yelp/
DATA_OUT=$ROOT/data
DONE=$ROOT/data/.done_prep
say() { echo "$(date '+%F %T') $*"; }

[ -f "$DONE" ] && { say "data prep already done ($DONE exists); exit"; exit 0; }

# Use the preferdiff env (Python 3.10, torch 2.5) for the prep script — no special deps
PY=~/miniconda3/envs/r10-preferdiff/bin/python

say "RQ10 data prep start"
say "STEAM source: $STEAM_SRC"
say "Output root:  $DATA_OUT"

# ── Sequential track: Beauty, Sports, Yelp ──────────────────────────────────
say "--- sequential noise injection ---"
$PY $SCRIPTS/noise_inject.py \
    --src_root "$STEAM_SRC" \
    --dst_root "$DATA_OUT" \
    --datasets Beauty Sports Yelp \
    --levels N0 N2_20 N3_30 \
    --also_recbole

rc=$?
if [ $rc -ne 0 ]; then
    say "ERROR: noise injection failed (rc=$rc); check log"
    exit $rc
fi

# ── Verify outputs ────────────────────────────────────────────────────────────
say "--- verification ---"
for ds in Beauty Sports Yelp; do
    for level in N0 N2_20 N3_30; do
        d=$DATA_OUT/${ds}_${level}
        if [ -f "$d/train.dat" ]; then
            n=$(wc -l < "$d/train.dat")
            say "  ${ds}_${level}: $n train lines"
        else
            say "  MISSING: $d/train.dat"
        fi
    done
done

touch "$DONE"
say "RQ10 data prep complete; output at $DATA_OUT"
