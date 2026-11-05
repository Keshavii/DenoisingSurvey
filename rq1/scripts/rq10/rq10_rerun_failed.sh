#!/bin/bash
# rq10_rerun_failed.sh — re-runs jobs that failed due to concurrency / code bugs.
#
# Root causes fixed before this script:
#   1. STEAM OOM:    rq10hsd started before rq10run finished (wrong unit name check),
#                    causing HSD + STEAM to compete for 24 GB → OOM.
#                    Fix: this script runs all jobs sequentially, no overlap.
#   2. GDMSR:        nn.TransformerEncoderLayer(batch_first=True) unsupported in
#                    PyTorch 1.7.1. Fix: gdmsr_patch.py wraps the class at runtime.
#   3. HSD xlsx:     run_hsd_survey.py now patches openpyxl.load_workbook to handle
#                    a missing 'denoising-ml.xlsx' gracefully.
#   4. PreferDiff:   failed due to GPU contention; retry alone.
#
# Jobs skipped (have .done files from prior successful runs):
#   GBSR (all 6), HDSR default, FMLP Beauty noise (all 3)
#
# Start unattended:
#   systemd-run --user --unit=rq10rerun --collect \
#     bash -c "bash ~/survey/rq1/scripts/rq10/rq10_rerun_failed.sh > ~/rq10_rerun.log 2>&1"
set -u
ROOT=${ROOT:-$HOME/survey/rq10}
R=$ROOT/repos
L=$ROOT/logs
RES=$ROOT/results
DATA=$ROOT/data
SCRIPTS=$HOME/survey/rq1/scripts/rq10
LIMIT=${LIMIT:-12h}
mkdir -p "$L" "$RES"
say() { echo "$(date '+%F %T') $*"; }

run() {  # run <name> <env> <dir> <cmd...>
  local n=$1 env=$2 dir=$3; shift 3
  [ -f "$L/run_${n}.done" ] && { say "$n: already done, skip"; return 0; }
  [ -f "$ROOT/envs_ok/$env" ] || { say "$n: env r10-$env not ready, skip"; return 1; }
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
  say "$n: exit $rc  ${mins} min  peak ${mib:-?} MiB"
}

# ── GDMSR: Beauty/Sports/Yelp × 3 datasets ───────────────────────────────────
# Fix: gdmsr_patch.py wraps TransformerEncoderLayer to strip batch_first=True
# at runtime (PyTorch 1.7 doesn't support it).
say "=== GDMSR (batch_first patch applied) ==="
# Copy patch into the gdmsr repo
cp "$SCRIPTS/gdmsr_patch.py" "$R/gdmsr/" 2>/dev/null \
  && say "copied gdmsr_patch.py"
for DS in yelp ciao douban; do
  mkdir -p "$R/gdmsr/log/$DS"
  run "gdmsr_${DS}" gdmsr "$R/gdmsr" python gdmsr_patch.py --dataset_name "$DS"
done

# ── STEAM baselines: Beauty/Sports/Yelp ──────────────────────────────────────
# Fix: runs sequentially AFTER GDMSR frees GPU; no concurrent HSD.
say "=== STEAM baselines ==="
for DS in Beauty Sports Yelp; do
  D=$R/steam/$DS
  [ -d "$D" ] || { say "skip steam_${DS,,}: dir $D not found"; continue; }
  NAME="steam_${DS,,}"
  run $NAME steam "$R/steam" \
    bash -c "python main.py -tf $D/train.dat -vf $D/valid.dat -ef $D/test.dat \
             -vn $D/valid_neg.dat -en $D/test_neg.dat -o ./save_${NAME}/ -m=train && \
             python main.py -tf $D/train.dat -vf $D/valid.dat -ef $D/test.dat \
             -vn $D/valid_neg.dat -en $D/test_neg.dat -o ./save_${NAME}/ -m=valid && \
             python main.py -tf $D/train.dat -vf $D/valid.dat -ef $D/test.dat \
             -vn $D/valid_neg.dat -en $D/test_neg.dat -o ./save_${NAME}/ -m=test"
done

# ── STEAM noise: Beauty/Sports/Yelp × {N0, N2_20, N3_30} ────────────────────
# Fix: runs after STEAM baselines free GPU. No concurrent HSD.
say "=== STEAM noise runs ==="
for DS in Beauty Sports Yelp; do
  for LEVEL in N0 N2_20 N3_30; do
    D=$DATA/${DS}_${LEVEL}
    [ -d "$D" ] || { say "skip: $D not found"; continue; }
    NAME="steam_${DS,,}_${LEVEL,,}"
    run $NAME steam "$R/steam" \
      bash -c "python main.py -tf $D/train.dat -vf $D/valid.dat -ef $D/test.dat \
               -vn $D/valid_neg.dat -en $D/test_neg.dat -o ./save_${NAME}/ -m=train && \
               python main.py -tf $D/train.dat -vf $D/valid.dat -ef $D/test.dat \
               -vn $D/valid_neg.dat -en $D/test_neg.dat -o ./save_${NAME}/ -m=valid && \
               python main.py -tf $D/train.dat -vf $D/valid.dat -ef $D/test.dat \
               -vn $D/valid_neg.dat -en $D/test_neg.dat -o ./save_${NAME}/ -m=test"
  done
done

# ── FMLP baselines: Beauty/Sports/Yelp ───────────────────────────────────────
# Original main.py; runs after STEAM frees GPU.
say "=== FMLP baselines ==="
for DS in Beauty Sports Yelp; do
  TXT=$R/fmlp/data/$DS.txt
  [ -f "$TXT" ] || { say "skip fmlp_${DS,,}: $TXT not found"; continue; }
  run "fmlp_${DS,,}" fmlp "$R/fmlp" python main.py --data_name "$DS"
done

# ── FMLP noise: Sports/Yelp × {N0, N2_20, N3_30} ────────────────────────────
# Beauty noise runs already succeeded; .done files will skip them.
say "=== FMLP noise (Sports/Yelp) ==="
cp "$SCRIPTS/run_fmlp_noise.py" "$R/fmlp/" 2>/dev/null
for DS in Sports Yelp; do
  for LEVEL in N0 N2_20 N3_30; do
    TXT=$R/fmlp/data/${DS}_${LEVEL}.txt
    [ -f "$TXT" ] || { say "skip fmlp ${DS}_${LEVEL}: $TXT not found"; continue; }
    NAME="fmlp_${DS,,}_${LEVEL,,}"
    run $NAME fmlp "$R/fmlp" python run_fmlp_noise.py --data_name="${DS}_${LEVEL}"
  done
done

# ── PreferDiff: Beauty (retry alone) ─────────────────────────────────────────
say "=== PreferDiff baseline (retry) ==="
run "preferdiff_beauty" preferdiff "$R/preferdiff" python main.py

# ── HSD: Sports/Yelp (Beauty results already in log; .done not set so retry) ─
# Fix: openpyxl patch in run_hsd_survey.py handles missing denoising-ml.xlsx.
say "=== HSD Sports/Yelp ==="
cp "$SCRIPTS/run_hsd_survey.py" "$R/hsd/" 2>/dev/null \
  && say "copied run_hsd_survey.py (xlsx patch included)"
for DS in Sports Yelp; do
  [ -f "$R/hsd/dataset/$DS/$DS.inter" ] || { say "  skip hsd_${DS,,}: no .inter"; continue; }
  run "hsd_${DS,,}_sasrec" recbole "$R/hsd" \
    python run_hsd_survey.py --dataset "$DS" --sub_model SASRec
done

# ── HSD: Beauty retry (xlsx crash means no .done; Beauty .inter exists) ──────
say "=== HSD Beauty (retry with xlsx patch) ==="
[ -f "$R/hsd/dataset/Beauty/Beauty.inter" ] && \
  run "hsd_beauty_sasrec" recbole "$R/hsd" \
    python run_hsd_survey.py --dataset Beauty --sub_model SASRec

say "=== rq10_rerun_failed complete ==="
echo ""
say "Summary (new entries):"
column -t "$RES/run_summary.tsv" 2>/dev/null | tail -20 || tail -20 "$RES/run_summary.tsv"
