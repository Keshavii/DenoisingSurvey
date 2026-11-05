#!/bin/bash
# RQ10 stage 1 on PC3 (6 Nov 2026): the home-data reproduction runs that failed on 5 Nov, fixed through run
# arguments, data and wrappers only (no change to any authors' code). Run by pc3_queue.sh; resumable (.done markers).
#
#   GDMSR   README run.sh settings (--gpu_id 0: the default 1 does not exist on a one-GPU PC) and, for ciao and
#           douban, --data_dir (it defaults to ./data/yelp); gdmsr_patch.py strips batch_first (PyTorch 1.7.1).
#   STEAM   -n item count per dataset, as its README asks ("revise ... item_num"): max item id + 3
#           (Beauty 12101 -> 12104, the default; Sports 18357 -> 18360; Yelp 16552 -> 16555).
#   FMLP    Sports_and_Outdoors and Yelp come from the authors' Google Drive folder (README); only Beauty ships in
#           the repository. Original main.py, names from its own dataset list.
#   HSD     run_hsd_survey.py saves the result as JSON (the authors' xlsx recorder raises TypeError at this commit).
#   PreferDiff  nothing to run: its README command (--sd=O, Sports) finished in the 4 Nov reproduction
#           (repro_preferdiff); the code maps only C, O, T (no Beauty).
# Also retires the FMLP Beauty noise results of 5 Nov: the noise was inserted at any position, so it replaced the
# test target of 14.6% (N2_20) and 18.2% (N3_30) of users. Their .done markers become .invalid.
set -u
ROOT=${ROOT:-$HOME/survey/rq10}
R=$ROOT/repos
L=$ROOT/logs
RES=$ROOT/results
SCRIPTS=$HOME/survey/rq1/scripts/rq10
LIMIT=${LIMIT:-12h}
mkdir -p "$L" "$RES"
say() { echo "$(date '+%F %T') [rq10-stage1] $*"; }

run() {  # run <name> <env> <dir> <cmd...>   (as in rq10_rerun_failed.sh)
  local n=$1 env=$2 dir=$3; shift 3
  [ -f "$L/run_${n}.done" ] && { say "$n: already done, skip"; return 0; }
  [ -f "$ROOT/envs_ok/$env" ] || { say "$n: env r10-$env not ready, skip"; return 1; }
  say "$n: start  cmd=$*"
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
  say "$n: exit $rc  ${mins} min  peak ${mib:-?} MiB  (log $L/run_${n}.log)"
  return $rc
}

say "start"
for n in fmlp_beauty_n2_20 fmlp_beauty_n3_30; do
  [ -f "$L/run_${n}.done" ] && mv "$L/run_${n}.done" "$L/run_${n}.invalid" && say "$n: retired (test targets overwritten by noise)"
done

say "=== GDMSR (README settings, GPU 0, per-dataset data folder) ==="
cp "$SCRIPTS/gdmsr_patch.py" "$R/gdmsr/"
for DS in yelp ciao douban; do
  mkdir -p "$R/gdmsr/log/$DS"
  run "gdmsr_${DS}" gdmsr "$R/gdmsr" python gdmsr_patch.py --lr 0.0001 --gpu_id 0 --early_stop 20 --epochs 200 \
      --data_loader_workers 10 --l2_reg 0.0001 --dataset_name "$DS" --data_dir "./data/$DS"
done

say "=== STEAM Sports and Yelp (item count per dataset) ==="
for spec in "Sports 18360" "Yelp 16555"; do
  set -- $spec; DS=$1; N=$2; D=./$DS; NAME="steam_${DS,,}"
  A="-tf $D/train.dat -vf $D/valid.dat -ef $D/test.dat -vn $D/valid_neg.dat -en $D/test_neg.dat -n $N -o ./save_${NAME}/"
  run "$NAME" steam "$R/steam" bash -c "python main.py $A -m=train && python main.py $A -m=valid && python main.py $A -m=test"
done

say "=== FMLP Sports and Yelp (authors' Google Drive data) ==="
F=$R/fmlp/data
if [ ! -s "$F/Sports_and_Outdoors.txt" ] || [ ! -s "$F/Yelp.txt" ]; then
  G=$ROOT/envs/gdown
  [ -x "$G/bin/gdown" ] || { ~/miniconda3/bin/conda create -y -q -p "$G" python=3.10 pip > /dev/null 2>&1 && "$G/bin/pip" install -q gdown; }
  mkdir -p "$ROOT/downloads/fmlp_drive"
  timeout 1h "$G/bin/gdown" --folder "https://drive.google.com/drive/folders/1omfrWZiYwmj3eFpIpb-8O29wbt4SVGzP" \
      -O "$ROOT/downloads/fmlp_drive" --remaining-ok > "$L/fmlp_drive_download.log" 2>&1 \
    || say "Google Drive download returned an error (see $L/fmlp_drive_download.log)"
  for f in Sports_and_Outdoors.txt Sports_and_Outdoors_sample.txt Yelp.txt Yelp_sample.txt; do
    p=$(find "$ROOT/downloads/fmlp_drive" -name "$f" -size +0 | head -1)
    [ -n "$p" ] && [ ! -s "$F/$f" ] && cp "$p" "$F/$f" && say "  $f from the Drive folder"
  done
fi
for DS in Sports_and_Outdoors Yelp; do
  if [ -s "$F/$DS.txt" ] && [ -s "$F/${DS}_sample.txt" ]; then
    run "fmlp_${DS,,}" fmlp "$R/fmlp" python main.py --data_name="$DS"
  else
    say "fmlp_${DS,,}: no $DS.txt / ${DS}_sample.txt (Drive download failed); skipped"
  fi
done

say "=== HSD Beauty, Sports, Yelp (SASRec; result saved as JSON) ==="
cp "$SCRIPTS/run_hsd_survey.py" "$R/hsd/"
for DS in Beauty Sports Yelp; do
  [ -f "$R/hsd/dataset/$DS/$DS.inter" ] || { say "hsd_${DS,,}_sasrec: no $DS.inter; skipped"; continue; }
  run "hsd_${DS,,}_sasrec" recbole "$R/hsd" python run_hsd_survey.py --dataset "$DS" --sub_model SASRec
done

# Stage 2 runs right after stage 1 (same log): the design's noise and full-ranking scores (rq10_stage2.sh)
say "=== stage 2 (log continues below) ==="
bash "$SCRIPTS/rq10_stage2.sh"

JOBS="gdmsr_yelp gdmsr_ciao gdmsr_douban steam_sports steam_yelp fmlp_sports_and_outdoors fmlp_yelp hsd_beauty_sasrec hsd_sports_sasrec hsd_yelp_sasrec"
OK=0; MISSING=""
for n in $JOBS; do if [ -f "$L/run_${n}.done" ]; then OK=$((OK + 1)); else MISSING="$MISSING $n"; fi; done
say "stage 1 complete: $OK of 10 jobs have results${MISSING:+; without:$MISSING} (stage 2: see results/stage2_summary.tsv)"
