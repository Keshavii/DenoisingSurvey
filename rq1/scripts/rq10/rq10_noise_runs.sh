#!/bin/bash
# RQ10 noise-condition runs: runs all sequential specialists on
# Beauty/Sports/Yelp × {N0, N2_20, N3_30}.
# Waits for rq10_data_prep.sh to finish before starting.
# Runs alongside / after rq10_run.sh (baseline runs); .done files prevent re-runs.
#
# Start unattended:
#   systemd-run --user --unit=rq10noise --collect \
#     bash -c "bash ~/survey/rq1/scripts/rq10/rq10_noise_runs.sh > ~/rq10_noise.log 2>&1"
set -u
ROOT=${ROOT:-$HOME/survey/rq10}
R=$ROOT/repos
L=$ROOT/logs
RES=$ROOT/results
DATA=$ROOT/data
LIMIT=${LIMIT:-12h}
mkdir -p "$L" "$RES"
say() { echo "$(date '+%F %T') $*"; }

# ── Wait for data prep ───────────────────────────────────────────────────────
say "waiting for rq10data prep to finish..."
while systemctl --user is-active --quiet rq10data 2>/dev/null; do sleep 60; done
[ -f "$DATA/.done_prep" ] || { say "ERROR: data prep not done ($DATA/.done_prep missing); abort"; exit 1; }
say "data ready"

# ── Wait for baseline GPU jobs (GBSR/HDSR/GDMSR) to free GPU memory ──────────
# STEAM needs ~3.5 GiB; GBSR uses ~12 GiB while running; they cannot share.
say "waiting for baseline GPU jobs (GBSR/HDSR/GDMSR) to finish..."
while pgrep -f "run_GBSR\.py|run_HDSR_pc3\.py|gdmsr/main\.py" > /dev/null 2>&1; do
  sleep 60
done
say "baseline GPU jobs done; GPU free for noise runs"

run() {  # run <name> <env> <dir> <cmd...>
  local n=$1 env=$2 dir=$3; shift 3
  [ -f "$L/run_${n}.done" ] && { say "$n: already done, skip"; return 0; }
  [ -f "$ROOT/envs_ok/$env" ] || { say "$n: env r10-$env not ready, skip"; printf "%s\tno-env\t0\t0\n" "$n" >> "$RES/noise_summary.tsv"; return 1; }
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
  printf "%s\t%s\t%s\t%s\n" "$n" "$rc" "$mins" "${mib:-0}" >> "$RES/noise_summary.tsv"
  [ $rc -eq 0 ] && touch "$L/run_${n}.done"
  say "$n: exit $rc  ${mins} min  peak ${mib:-?} MiB"
}

# ── STEAM: Beauty/Sports/Yelp × {N0, N2_20, N3_30} ──────────────────────────
say "=== STEAM noise runs ==="
for DS in Beauty Sports Yelp; do
  for LEVEL in N0 N2_20 N3_30; do
    D=$DATA/${DS}_${LEVEL}
    [ -d "$D" ] || { say "skip: $D not found"; continue; }
    NAME="steam_${DS,,}_${LEVEL,,}"   # e.g. steam_beauty_n0
    run $NAME steam $R/steam \
      bash -c "python main.py -tf $D/train.dat -vf $D/valid.dat -ef $D/test.dat \
               -vn $D/valid_neg.dat -en $D/test_neg.dat -o ./save_${NAME}/ -m=train && \
               python main.py -tf $D/train.dat -vf $D/valid.dat -ef $D/test.dat \
               -vn $D/valid_neg.dat -en $D/test_neg.dat -o ./save_${NAME}/ -m=valid && \
               python main.py -tf $D/train.dat -vf $D/valid.dat -ef $D/test.dat \
               -vn $D/valid_neg.dat -en $D/test_neg.dat -o ./save_${NAME}/ -m=test"
  done
done

# ── FMLP-Rec: Beauty/Sports × {N0, N2_20, N3_30} ────────────────────────────
# FMLP uses --data_name=<X> and loads repos/fmlp/data/<X>.txt (space-sep seqs).
# rq10_data_prep.sh writes Beauty_N2_20.txt etc. directly into fmlp/data/.
say "=== FMLP-Rec noise runs ==="
for DS in Beauty Sports; do
  for LEVEL in N0 N2_20 N3_30; do
    TXT=$R/fmlp/data/${DS}_${LEVEL}.txt
    [ -f "$TXT" ] || { say "skip fmlp ${DS}_${LEVEL}: $TXT not found (data prep may have skipped it)"; continue; }
    NAME="fmlp_${DS,,}_${LEVEL,,}"
    run $NAME fmlp $R/fmlp python main.py --data_name="${DS}_${LEVEL}"
  done
done

# ── PreferDiff: Beauty only × {N0, N2_20, N3_30} ────────────────────────────
# PreferDiff has no --data_name arg; we cannot switch datasets without editing code.
# Skip noise runs for now; only the baseline (Beauty default) is in rq10_run.sh.
say "=== PreferDiff: noise runs skipped (no dataset arg in main.py) ==="

say "=== RQ10 noise runs complete ==="
echo ""
say "Summary:"
column -t "$RES/noise_summary.tsv" 2>/dev/null || cat "$RES/noise_summary.tsv"
