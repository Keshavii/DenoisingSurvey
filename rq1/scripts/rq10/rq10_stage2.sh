#!/bin/bash
# RQ10 stage 2 on PC3: the sequential specialists under the design's noise and one scoring protocol.
# Run by pc3_queue.sh after stage 1; resumable (.done markers); every job runs alone on the GPU.
#
# Data (scripts/rq10/seq_noise.py): FMLP's files (the design's versions) for Beauty, Sports_and_Outdoors, Yelp;
#   levels N0 (as collected), I10, I20 (one random item inserted before a training item with probability 0.1 / 0.2;
#   validation and test items never change); the same noisy sequences in FMLP, STEAM and RecBole format.
#   Sports falls back to STEAM's copy (same 35.6k users / 18,357 items) if the Drive download of stage 1 failed;
#   Yelp has no fallback (STEAM's Yelp is another version) and is skipped then.
# Scoring: leave-one-out, full ranking over all items, the user's earlier items excluded, Recall@10 and NDCG@10:
#   FMLP-Rec --full_sort (its README flag); HSD RecBole full mode (its own config); STEAM steam_full_eval.py on the
#   best validation epoch (STEAM's own selection), corrected sequence. Table: results/stage2_summary.tsv.
# Settings: each method's defaults (README); one noise draw (seed 1) unless SEEDS is set.
set -u
ROOT=${ROOT:-$HOME/survey/rq10}
R=$ROOT/repos
L=$ROOT/logs
RES=$ROOT/results
SCRIPTS=$HOME/survey/rq1/scripts/rq10
LIMIT=${LIMIT:-12h}
SEEDS=${SEEDS:-1}
LEVELS=${LEVELS:-N0 I10 I20}
DSETS=${DSETS:-Beauty Sports_and_Outdoors Yelp}
STEAM_EPOCHS=${STEAM_EPOCHS:-300}      # STEAM's default (-e 300)
FMLP_ARGS=${FMLP_ARGS:-}               # empty = FMLP's defaults
STEAM_ARGS=${STEAM_ARGS:-}             # empty = STEAM's defaults
PY3=${PY3:-python3}
F=$R/fmlp/data
S2=$ROOT/data_s2
mkdir -p "$L" "$RES" "$S2"
say() { echo "$(date '+%F %T') [rq10-stage2] $*"; }

run() {  # run <name> <env> <dir> <cmd...>   (as in rq10_stage1.sh)
  local n=$1 env=$2 dir=$3; shift 3
  [ -f "$L/run_${n}.done" ] && { say "$n: already done, skip"; return 0; }
  [ -f "$ROOT/envs_ok/$env" ] || { say "$n: env r10-$env not ready, skip"; return 1; }
  say "$n: start"
  local peak=$L/run_${n}.gpu t0; t0=$(date +%s)
  ( while true; do nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null; sleep 5; done ) > "$peak" &
  local mon=$!
  (cd "$dir" && \
    PATH=~/miniconda3/envs/r10-$env/bin:$PATH \
    LD_LIBRARY_PATH=~/miniconda3/envs/r10-$env/lib \
    timeout "$LIMIT" "$@") > "$L/run_${n}.log" 2>&1
  local rc=$?
  kill $mon 2>/dev/null; wait $mon 2>/dev/null
  local mins=$(( ($(date +%s) - t0) / 60 ))
  local mib; mib=$(sort -n "$peak" 2>/dev/null | tail -1)
  printf "%s\t%s\t%s\t%s\n" "$n" "$rc" "$mins" "${mib:-0}" >> "$RES/run_summary.tsv"
  [ $rc -eq 0 ] && touch "$L/run_${n}.done"
  say "$n: exit $rc  ${mins} min  peak ${mib:-?} MiB"
  return $rc
}

say "start (datasets [$DSETS], levels [$LEVELS], seeds [$SEEDS])"

# Sports fallback: STEAM's copy written in FMLP's format (user = line number, sequence = test.dat, negatives = test_neg)
if [ ! -s "$F/Sports_and_Outdoors.txt" ] && [ -s "$R/steam/Sports/test.dat" ]; then
  "$PY3" - "$R/steam/Sports" "$F" <<'EOF' && say "Sports_and_Outdoors: built from STEAM's Sports (Drive copy missing)"
import os, sys
src, dst = sys.argv[1:3]
with open(os.path.join(src, "test.dat")) as a, open(os.path.join(src, "test_neg.dat")) as b, \
     open(os.path.join(dst, "Sports_and_Outdoors.txt.tmp"), "w") as fa, open(os.path.join(dst, "Sports_and_Outdoors_sample.txt.tmp"), "w") as fb:
    for u, (s, n) in enumerate(zip(a, b), 1):
        fa.write(f"{u} " + " ".join(x for x in s.strip().split(",") if x) + "\n")
        fb.write(f"{u} " + " ".join(x for x in n.strip().split(",") if x) + "\n")
for k in ("Sports_and_Outdoors.txt", "Sports_and_Outdoors_sample.txt"):
    os.replace(os.path.join(dst, k + ".tmp"), os.path.join(dst, k))
open(os.path.join(dst, "Sports_and_Outdoors.SOURCE"), "w").write(
    "STEAM's Sports (latest 50 items per user: 35,597 users, 18,357 items, 294,483 interactions), written in FMLP's "
    "format because the authors' Drive file was not available; FMLP's own file has 35,598 / 18,357 / 296,337.\n")
EOF
fi

READY=""
for DS in $DSETS; do
  if [ -s "$F/$DS.txt" ] && [ -s "$F/${DS}_sample.txt" ]; then READY="$READY $DS"; else say "$DS: no FMLP files ($F/$DS.txt); skipped"; fi
done
[ -n "$READY" ] || { say "no dataset available; stage 2 complete: 0 runs"; exit 0; }

say "noise files [$READY ]"
"$PY3" "$SCRIPTS/seq_noise.py" --fmlp_data "$F" --datasets $READY --levels $LEVELS --seeds $SEEDS \
    --steam_root "$S2" --recbole_root "$R/hsd/dataset" > "$L/stage2_noise.log" 2>&1 \
  || { say "seq_noise.py failed (see $L/stage2_noise.log)"; exit 1; }
cp "$SCRIPTS/run_fmlp_noise.py" "$R/fmlp/"
cp "$SCRIPTS/steam_full_eval.py" "$R/steam/"
cp "$SCRIPTS/run_hsd_survey.py" "$R/hsd/"

for SEED in $SEEDS; do
  for LV in $LEVELS; do
    for DS in $READY; do
      NAME=${DS}_${LV}_s${SEED}; LOW=$(echo "$NAME" | tr 'A-Z' 'a-z')
      N=$("$PY3" -c "import json;print(json.load(open('$F/$NAME.meta.json'))['steam_n'])")
      run "s2_fmlp_$LOW" fmlp "$R/fmlp" python run_fmlp_noise.py --data_name="$NAME" --full_sort $FMLP_ARGS
      run "s2_hsd_$LOW" recbole "$R/hsd" python run_hsd_survey.py --dataset "$NAME" --sub_model SASRec
      D=$S2/$NAME; O=./save_s2_$NAME/
      # more items than Beauty (12,101): STEAM's batch 256 runs out of the 4090's 24 GB (13 Nov), so batch 128 (deviation)
      BIG=""; [ "$N" -gt 12104 ] && BIG="-b 128"
      A="-tf $D/train.dat -vf $D/valid.dat -ef $D/test.dat -vn $D/valid_neg.dat -en $D/test_neg.dat -n $N -o $O -e $STEAM_EPOCHS $BIG $STEAM_ARGS"
      run "s2_steam_$LOW" steam "$R/steam" bash -c "python main.py $A -m=train && python main.py $A -m=valid && \
          python steam_full_eval.py -ef $D/test.dat -en $D/test_neg.dat -n $N -o $O $BIG $STEAM_ARGS --out $RES/s2_steam_$NAME.json"
    done
  done
done

"$PY3" "$SCRIPTS/rq10_collect.py" --root "$ROOT" || say "collect failed"
DONE=$(find "$L" -maxdepth 1 -name 'run_s2_*.done' | wc -l)
say "stage 2 complete: $DONE runs with results (table: $RES/stage2_summary.tsv)"
