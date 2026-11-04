#!/bin/bash
# RQ10 data preparation on PC3: creates N0/N2_20/N3_30 noise variants for
# the sequential track in both STEAM and FMLP formats.
#
# STEAM: writes ~/survey/rq10/data/<Dataset>_<Level>/ (Beauty/Sports/Yelp)
# FMLP:  writes ~/survey/rq10/repos/fmlp/data/<Dataset>_<Level>.txt
#
# Social datasets (GBSR/GDMSR/HDSR) handle noise inside their own run args;
# no data-prep step needed for them.
#
# Run unattended:
#   systemd-run --user --unit=rq10data --collect \
#     bash -c "bash ~/survey/rq1/scripts/rq10/rq10_data_prep.sh > ~/rq10_data_prep.log 2>&1"
set -u
ROOT=${ROOT:-$HOME/survey/rq10}
SCRIPTS=$HOME/survey/rq1/scripts/rq10
STEAM_SRC=$ROOT/repos/steam    # ships Beauty/, Sports/, Yelp/ subdirs
FMLP_DATA=$ROOT/repos/fmlp/data  # ships Beauty.txt, Sports.txt, Yelp.txt (or subset)
DATA_OUT=$ROOT/data
DONE=$ROOT/data/.done_prep
say() { echo "$(date '+%F %T') $*"; }

[ -f "$DONE" ] && { say "data prep already done ($DONE exists); exit 0"; exit 0; }
mkdir -p "$DATA_OUT"

# Use the preferdiff env (Python 3.10, no special deps needed for this script)
PY=~/miniconda3/envs/r10-preferdiff/bin/python

say "RQ10 data prep start"

# ── STEAM format: Beauty, Sports, Yelp ──────────────────────────────────────
say "--- STEAM format noise injection ---"
$PY "$SCRIPTS/noise_inject.py" \
    --mode steam \
    --src_root "$STEAM_SRC" \
    --dst_root "$DATA_OUT" \
    --datasets Beauty Sports Yelp \
    --levels N0 N2_20 N3_30
rc=$?
[ $rc -ne 0 ] && { say "ERROR: STEAM noise injection failed (rc=$rc)"; exit $rc; }

# ── FMLP format: Beauty (Sports/Yelp only if the .txt files exist) ───────────
say "--- FMLP format noise injection ---"
# Determine which datasets are present
FMLP_DATASETS=""
for ds in Beauty Sports Yelp; do
    [ -f "$FMLP_DATA/$ds.txt" ] && FMLP_DATASETS="$FMLP_DATASETS $ds"
done
FMLP_DATASETS="${FMLP_DATASETS# }"  # trim leading space

if [ -n "$FMLP_DATASETS" ]; then
    say "FMLP datasets found: $FMLP_DATASETS"
    $PY "$SCRIPTS/noise_inject.py" \
        --mode fmlp \
        --src_root "$FMLP_DATA" \
        --dst_root "$FMLP_DATA" \
        --datasets $FMLP_DATASETS \
        --levels N0 N2_20 N3_30
    rc=$?
    [ $rc -ne 0 ] && { say "ERROR: FMLP noise injection failed (rc=$rc)"; exit $rc; }
else
    say "FMLP: no .txt files found in $FMLP_DATA; skipping"
fi

# ── Verify outputs ────────────────────────────────────────────────────────────
say "--- verification ---"
for ds in Beauty Sports Yelp; do
    for level in N0 N2_20 N3_30; do
        d="$DATA_OUT/${ds}_${level}"
        if [ -f "$d/train.dat" ]; then
            n=$(wc -l < "$d/train.dat")
            say "  STEAM ${ds}_${level}: ${n} train users"
        else
            say "  MISSING: $d/train.dat"
        fi
        f="$FMLP_DATA/${ds}_${level}.txt"
        [ -f "$f" ] && say "  FMLP  ${ds}_${level}: $(wc -l < "$f") users"
    done
done

touch "$DONE"
say "RQ10 data prep complete"
