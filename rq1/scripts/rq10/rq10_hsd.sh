#!/bin/bash
# RQ10 HSD + SSDRec runs (RecBole-based, SASRec backbone).
# Runs AFTER rq10run finishes (waits for it; .done files prevent re-runs).
#
# Data pipeline:
#   1. Convert FMLP .txt or STEAM .dat → RecBole .inter (idempotent)
#   2. Copy .inter to both hsd/dataset/ and ssdrec/dataset/
#   3. Run HSD for Beauty/Sports/Yelp × SASRec backbone
#   4. Run SSDRec for Beauty/Sports/Yelp × SASRec backbone
#
# Start unattended:
#   systemd-run --user --unit=rq10hsd --collect \
#     bash -c "bash ~/survey/rq1/scripts/rq10/rq10_hsd.sh > ~/rq10_hsd.log 2>&1"
set -u
ROOT=${ROOT:-$HOME/survey/rq10}
R=$ROOT/repos
L=$ROOT/logs
RES=$ROOT/results
SCRIPTS=$HOME/survey/rq1/scripts/rq10
LIMIT=${LIMIT:-12h}
mkdir -p "$L" "$RES"
say() { echo "$(date '+%F %T') $*"; }

# ── Wait for rq10run (baseline) to finish ────────────────────────────────────
say "waiting for rq10run to finish..."
while systemctl --user is-active --quiet rq10run 2>/dev/null; do sleep 60; done
say "rq10run done (or never started as a unit); proceeding"

# Python from recbole env (RecBole 1.0.1 installed)
PY=~/miniconda3/envs/r10-recbole/bin/python
[ -f "$ROOT/envs_ok/recbole" ] || { say "ERROR: r10-recbole env not ready ($ROOT/envs_ok/recbole missing); abort"; exit 1; }

run() {  # run <name> <env> <dir> <cmd...>
  local n=$1 env=$2 dir=$3; shift 3
  [ -f "$L/run_${n}.done" ] && { say "$n: already done, skip"; return 0; }
  [ -f "$ROOT/envs_ok/$env" ] || { say "$n: env r10-$env not ready, skip"; printf "%s\tno-env\t0\t0\n" "$n" >> "$RES/run_summary.tsv"; return 1; }
  say "$n: start  cmd=$*"
  local peak=$L/run_${n}.gpu t0=$(date +%s)
  ( while true; do nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null; sleep 5; done ) > "$peak" &
  local mon=$!
  (cd "$dir" && \
    PATH=~/miniconda3/envs/r10-$env/bin:$PATH \
    LD_LIBRARY_PATH=~/miniconda3/envs/r10-$env/lib \
    timeout $LIMIT "$@") > "$L/run_${n}.log" 2>&1
  local rc=$?
  kill $mon 2>/dev/null; wait $mon 2>/dev/null
  local mins=$(( ($(date +%s) - t0) / 60 ))
  local mib; mib=$(sort -n "$peak" 2>/dev/null | tail -1)
  printf "%s\t%s\t%s\t%s\n" "$n" "$rc" "$mins" "${mib:-0}" >> "$RES/run_summary.tsv"
  [ $rc -eq 0 ] && touch "$L/run_${n}.done"
  say "$n: exit $rc  ${mins} min  peak ${mib:-?} MiB  (rc=124 means time limit)"
}

# ── Data conversion: FMLP/STEAM → RecBole .inter ────────────────────────────
say "=== RecBole data conversion ==="
for DS in Beauty Sports Yelp; do
  INTER=$R/hsd/dataset/$DS/$DS.inter
  if [ -f "$INTER" ]; then
    say "  $DS: .inter already exists, skip"
    continue
  fi
  # Prefer FMLP .txt (has explicit user IDs; cleaner mapping)
  if [ -f "$R/fmlp/data/$DS.txt" ]; then
    say "  $DS: converting from FMLP..."
    $PY "$SCRIPTS/fmlp_to_recbole.py" --mode fmlp \
        --src_root "$R/fmlp/data" \
        --dst_root "$R/hsd/dataset" \
        --datasets "$DS"
  elif [ -d "$R/steam/$DS" ]; then
    say "  $DS: FMLP not found, converting from STEAM..."
    $PY "$SCRIPTS/fmlp_to_recbole.py" --mode steam \
        --src_root "$R/steam" \
        --dst_root "$R/hsd/dataset" \
        --datasets "$DS"
  else
    say "  WARNING: no data source for $DS (no FMLP .txt or STEAM dir); skip"
    continue
  fi
done

# Share converted .inter files with SSDRec (same data, different model)
for DS in Beauty Sports Yelp; do
  INTER=$R/hsd/dataset/$DS/$DS.inter
  [ -f "$INTER" ] || continue
  mkdir -p "$R/ssdrec/dataset/$DS"
  [ -f "$R/ssdrec/dataset/$DS/$DS.inter" ] || cp "$INTER" "$R/ssdrec/dataset/$DS/"
done

# Copy wrapper scripts into the repos (run() cd's into the repo dir)
cp "$SCRIPTS/run_hsd_survey.py"    "$R/hsd/"    2>/dev/null && say "copied run_hsd_survey.py"
cp "$SCRIPTS/run_ssdrec_survey.py" "$R/ssdrec/" 2>/dev/null && say "copied run_ssdrec_survey.py"

# ── HSD: Beauty/Sports/Yelp × SASRec backbone ───────────────────────────────
say "=== HSD sequential track (RecBole, SASRec backbone) ==="
for DS in Beauty Sports Yelp; do
  [ -f "$R/hsd/dataset/$DS/$DS.inter" ] || { say "  skip hsd_${DS,,}: no .inter"; continue; }
  run "hsd_${DS,,}_sasrec" recbole "$R/hsd" \
    python run_hsd_survey.py --dataset "$DS" --sub_model SASRec
done

# ── SSDRec: Beauty/Sports/Yelp × SASRec backbone ────────────────────────────
# SSDRec augments HSD with social-graph signals; may fail if graph data for
# Beauty/Sports/Yelp is not available (original repo ships ml-10k graph only).
# It will log the error; the .done file is NOT written on failure so it stays
# skippable.
say "=== SSDRec sequential+graph track (RecBole, SASRec backbone) ==="
for DS in Beauty Sports Yelp; do
  [ -f "$R/ssdrec/dataset/$DS/$DS.inter" ] || { say "  skip ssdrec_${DS,,}: no .inter"; continue; }
  run "ssdrec_${DS,,}_sasrec" recbole "$R/ssdrec" \
    python run_ssdrec_survey.py --dataset "$DS" --sub_model SASRec
done

say "=== RQ10 HSD/SSDRec runs complete ==="
echo ""
say "Summary:"
column -t "$RES/run_summary.tsv" 2>/dev/null || cat "$RES/run_summary.tsv"
