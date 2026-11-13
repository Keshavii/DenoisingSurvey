#!/bin/bash
# RQ10 stage 3 on PC3 (13 Nov 2026): what stages 1-2 could not run, fixed. Run by pc3_queue.sh; resumable (.done markers,
# log ~/rq10_stage3.log). Every job runs alone on the GPU.
#   1. FMLP's home data (Sports_and_Outdoors, Yelp) from the authors' Google Drive folder. On 8 Nov gdown refused the
#      option --remaining-ok (not in the installed gdown), so nothing was downloaded. If the authors' Sports arrives,
#      stage 2's Sports runs (made on STEAM's copy, the fallback) are retired and rerun on the authors' file.
#   2. FMLP Sports_and_Outdoors and Yelp on that data (stage-1 jobs).
#   3. STEAM Sports and Yelp at batch 128: at STEAM's default batch 256 they ran out of memory alone on the 24 GB 4090
#      (Sports and Yelp have 1.5x and 1.4x Beauty's items; Beauty at batch 256 peaks at 22.7 GB). Recorded deviation.
#   4. Stage 2 again (it skips finished runs): STEAM Sports at batch 128, and Yelp for all three methods if it now exists.
#   5. GDMSR on CUDA 11.8: the README stack (torch 1.7.1, DGL 0.6.1 for CUDA 11.0) fails on the 4090 inside DGL
#      (coo2csr: CUSPARSE ERROR 10; CUDA 11.0 has no Ada support). Nearest working stack, recorded as a deviation:
#      Python 3.9, torch 2.0.1+cu118, DGL 1.1.3+cu118, numpy<2 (GDMSR's data pickles hold numpy arrays only).
#      GDMSR's code is unchanged; gdmsr_patch.py still strips batch_first (harmless on torch 2: same tensors).
#      A smoke test runs DGL's failing call on the GPU first; if it fails, GDMSR is skipped with the reason.
set -u
ROOT=${ROOT:-$HOME/survey/rq10}
R=$ROOT/repos
L=$ROOT/logs
RES=$ROOT/results
SCRIPTS=$HOME/survey/rq1/scripts/rq10
LIMIT=${LIMIT:-12h}
F=$R/fmlp/data
mkdir -p "$L" "$RES"
say() { echo "$(date '+%F %T') [rq10-stage3] $*"; }

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
  say "$n: exit $rc  ${mins} min  peak ${mib:-?} MiB  (log $L/run_${n}.log)"
  return $rc
}

say "start"

say "=== 1. FMLP home data from the authors' Google Drive folder ==="
if [ ! -s "$F/Yelp.txt" ] || [ -f "$F/Sports_and_Outdoors.SOURCE" ]; then
  G=$ROOT/envs/gdown
  [ -x "$G/bin/gdown" ] || { ~/miniconda3/bin/conda create -y -q -p "$G" python=3.10 pip > /dev/null 2>&1 && "$G/bin/pip" install -q gdown; }
  mkdir -p "$ROOT/downloads/fmlp_drive"
  timeout 1h "$G/bin/gdown" --folder "https://drive.google.com/drive/folders/1omfrWZiYwmj3eFpIpb-8O29wbt4SVGzP" \
      -O "$ROOT/downloads/fmlp_drive" > "$L/fmlp_drive_download.log" 2>&1 \
    || say "Google Drive download returned an error (see $L/fmlp_drive_download.log); using what arrived"
  for f in Yelp.txt Yelp_sample.txt; do
    p=$(find "$ROOT/downloads/fmlp_drive" -name "$f" -size +0 | head -1)
    [ -n "$p" ] && [ ! -s "$F/$f" ] && cp "$p" "$F/$f" && say "  $f from the Drive folder"
  done
  ps=$(find "$ROOT/downloads/fmlp_drive" -name "Sports_and_Outdoors.txt" -size +0 | head -1)
  pss=$(find "$ROOT/downloads/fmlp_drive" -name "Sports_and_Outdoors_sample.txt" -size +0 | head -1)
  if [ -n "$ps" ] && [ -n "$pss" ] && [ -f "$F/Sports_and_Outdoors.SOURCE" ]; then
    say "  authors' Sports_and_Outdoors arrived: replacing STEAM's copy and retiring stage 2's Sports runs"
    mkdir -p "$ROOT/retired/sports_fallback"
    mv "$F"/Sports_and_Outdoors* "$ROOT/retired/sports_fallback/" 2>/dev/null
    cp "$ps" "$F/Sports_and_Outdoors.txt"; cp "$pss" "$F/Sports_and_Outdoors_sample.txt"
    for d in "$L"/run_s2_*_sports_and_outdoors_*.done; do [ -f "$d" ] && mv "$d" "${d%.done}.invalid"; done
    rm -f "$R"/hsd/results/hsd_Sports_and_Outdoors_*.json "$RES"/s2_hsd_Sports_and_Outdoors_*.json "$RES"/s2_steam_Sports_and_Outdoors_*.json
  fi
fi

say "=== 2. FMLP Sports_and_Outdoors and Yelp (home data, stage-1 jobs) ==="
for DS in Sports_and_Outdoors Yelp; do
  if [ -s "$F/$DS.txt" ] && [ -s "$F/${DS}_sample.txt" ] && [ ! -f "$F/$DS.SOURCE" ]; then
    run "fmlp_${DS,,}" fmlp "$R/fmlp" python main.py --data_name="$DS"
  else
    say "fmlp_${DS,,}: the authors' $DS file is not here; skipped"
  fi
done

say "=== 3. STEAM Sports and Yelp at batch 128 (home data) ==="
for spec in "Sports 18360" "Yelp 16555"; do
  set -- $spec; DS=$1; N=$2; D=./$DS; NAME="steam_${DS,,}_b128"
  A="-tf $D/train.dat -vf $D/valid.dat -ef $D/test.dat -vn $D/valid_neg.dat -en $D/test_neg.dat -n $N -b 128 -o ./save_${NAME}/"
  run "$NAME" steam "$R/steam" bash -c "python main.py $A -m=train && python main.py $A -m=valid && python main.py $A -m=test"
done

say "=== 4. stage 2 again (finished runs are skipped) ==="
bash "$SCRIPTS/rq10_stage2.sh"

say "=== 5. GDMSR on CUDA 11.8 (README stack fails on the 4090: CUSPARSE ERROR 10) ==="
E=$HOME/miniconda3/envs/r10-gdmsr2
if [ ! -f "$ROOT/envs_ok/gdmsr2" ]; then
  if [ ! -x "$E/bin/python" ]; then
    timeout 30m ~/miniconda3/bin/conda create -y -q -n r10-gdmsr2 python=3.9 pip > "$L/gdmsr2_env.log" 2>&1
  fi
  timeout 30m "$E/bin/pip" install -q "torch==2.0.1+cu118" --index-url https://download.pytorch.org/whl/cu118 >> "$L/gdmsr2_env.log" 2>&1
  timeout 20m "$E/bin/pip" install -q "dgl==1.1.3+cu118" -f https://data.dgl.ai/wheels/cu118/repo.html \
      "numpy<2" pandas tqdm setproctitle "setuptools<70" packaging >> "$L/gdmsr2_env.log" 2>&1
  if "$E/bin/python" -c "import torch, dgl; g = dgl.graph(([0, 1], [1, 2])).to('cuda'); print('smoke ok', torch.__version__, dgl.__version__, g.out_degrees().tolist())" >> "$L/gdmsr2_env.log" 2>&1; then
    mkdir -p "$ROOT/envs_ok" && touch "$ROOT/envs_ok/gdmsr2" && say "env r10-gdmsr2 ready ($(tail -1 "$L/gdmsr2_env.log"))"
  else
    say "env r10-gdmsr2 failed its GPU smoke test (see $L/gdmsr2_env.log); GDMSR skipped"
  fi
fi
cp "$SCRIPTS/gdmsr_patch.py" "$R/gdmsr/"
for DS in yelp ciao douban; do
  mkdir -p "$R/gdmsr/log/$DS"
  run "gdmsr2_${DS}" gdmsr2 "$R/gdmsr" python gdmsr_patch.py --lr 0.0001 --gpu_id 0 --early_stop 20 --epochs 200 \
      --data_loader_workers 10 --l2_reg 0.0001 --dataset_name "$DS" --data_dir "./data/$DS"
done

OK=0; MISSING=""
for n in fmlp_sports_and_outdoors fmlp_yelp steam_sports_b128 steam_yelp_b128 gdmsr2_yelp gdmsr2_ciao gdmsr2_douban; do
  if [ -f "$L/run_${n}.done" ]; then OK=$((OK + 1)); else MISSING="$MISSING $n"; fi
done
say "stage 3 complete: $OK of 7 jobs have results${MISSING:+; without:$MISSING} (stage 2 table: results/stage2_summary.tsv)"
