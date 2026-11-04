#!/bin/bash
# RQ10 real runs — PC3 (RTX 4090): baseline reproductions on each method's home datasets.
# Establishes per-method baselines on clean data for RQ10 (specialist performance).
# Runs all 6 methods that can be tested on PC3; each job is resumable via .done files.
# Triggered by rq10_next.sh when this file + rq1/configs/rq10/READY both appear in git.
#
# Start manually:
#   systemd-run --user --unit=rq10run --collect \
#     bash -c "bash ~/survey/rq1/scripts/rq10_run.sh > ~/rq10_run.log 2>&1"
# Check progress:
#   cat ~/survey/rq10/results/run_summary.tsv | column -t
#   tail -f ~/rq10_run.log
set -u
ROOT=${ROOT:-$HOME/survey/rq10}
R=$ROOT/repos
L=$ROOT/logs
RES=$ROOT/results
LIMIT=${LIMIT:-12h}
mkdir -p "$L" "$RES"
say() { echo "$(date '+%F %T') $*"; }

run() {  # run <name> <env> <dir> <cmd...>
  local n=$1 env=$2 dir=$3; shift 3
  [ -f "$L/run_${n}.done" ] && { say "$n: already done, skip"; return 0; }
  [ -f "$ROOT/envs_ok/$env" ] || { say "$n: env r10-$env not ready, skip"; printf "%s\tno-env\t0\t0\n" "$n" >> "$RES/run_summary.tsv"; return 1; }
  say "$n: starting  dir=$dir  cmd=$*"
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

# ── SOCIAL TRACK: GBSR (social denoising on LightGCN-S backbone) ──────────────
# seed fixed at 2023 in run_GBSR.py; each call is one independent run.
# 3 datasets in repo; 2 passes (run1, run2) for variance via different tie assignment.
say "=== GBSR social track ==="
run gbsr_douban_r1   gbsr  $R/gbsr/torch_version  python run_GBSR.py --dataset douban_book --runid run1 --beta 40 --sigma 2.5
run gbsr_epinions_r1 gbsr  $R/gbsr/torch_version  python run_GBSR.py --dataset epinions    --runid run1 --beta 40 --sigma 2.5
run gbsr_yelp_r1     gbsr  $R/gbsr/torch_version  python run_GBSR.py --dataset yelp        --runid run1 --beta 40 --sigma 2.5
run gbsr_douban_r2   gbsr  $R/gbsr/torch_version  python run_GBSR.py --dataset douban_book --runid run2 --beta 40 --sigma 2.5
run gbsr_epinions_r2 gbsr  $R/gbsr/torch_version  python run_GBSR.py --dataset epinions    --runid run2 --beta 40 --sigma 2.5
run gbsr_yelp_r2     gbsr  $R/gbsr/torch_version  python run_GBSR.py --dataset yelp        --runid run2 --beta 40 --sigma 2.5

# ── SOCIAL TRACK: HDSR ────────────────────────────────────────────────────────
# Fix: code expects ./ckpts to exist; mkdir before run (not a code change).
# Dataset and device are set inside run_HDSR.py (README-sanctioned config);
# run_HDSR_pc3.py has device changed to cuda:0 (created by rq10_repro.sh; recreated here).
say "=== HDSR social track ==="
sed "s/config\['device'\] = 'cuda:1'/config['device'] = 'cuda:0'/" \
    $R/hdsr/src/run_HDSR.py > $R/hdsr/src/run_HDSR_pc3.py
mkdir -p $R/hdsr/src/ckpts
run hdsr_default  hdsr  $R/hdsr/src  python run_HDSR_pc3.py

# ── SOCIAL TRACK: GDMSR ───────────────────────────────────────────────────────
# Fix: code uses os.mkdir (not makedirs) for ./log/<dataset>; create log/ first.
# bash needed to source LD_LIBRARY_PATH for CUDA 11.0 / DGL; run.sh runs yelp by default.
say "=== GDMSR social track ==="
mkdir -p $R/gdmsr/log
run gdmsr_yelp   gdmsr  $R/gdmsr  bash run.sh
# Try ciao and douban via direct arg (run.sh likely wraps: python main.py --dataset_name=yelp)
run gdmsr_ciao   gdmsr  $R/gdmsr  bash -c "mkdir -p log/ciao   && python main.py --dataset_name=ciao"
run gdmsr_douban gdmsr  $R/gdmsr  bash -c "mkdir -p log/douban && python main.py --dataset_name=douban"

# ── SEQUENTIAL TRACK: STEAM (~128 min per dataset, 23 GB peak) ───────────────
# Dataset switching via file-path args: -tf/-vf/-ef/-vn/-en (no --data_name arg).
# repo ships Beauty, Sports, Yelp; run all three.
say "=== STEAM sequential track ==="
run steam_beauty steam  $R/steam  \
  bash -c "python main.py -m=train && python main.py -m=valid && python main.py -m=test"
run steam_sports steam  $R/steam  \
  bash -c "python main.py -tf ./Sports/train.dat -vf ./Sports/valid.dat -ef ./Sports/test.dat \
           -vn ./Sports/valid_neg.dat -en ./Sports/test_neg.dat -m=train && \
           python main.py -tf ./Sports/train.dat -vf ./Sports/valid.dat -ef ./Sports/test.dat \
           -vn ./Sports/valid_neg.dat -en ./Sports/test_neg.dat -m=valid && \
           python main.py -tf ./Sports/train.dat -vf ./Sports/valid.dat -ef ./Sports/test.dat \
           -vn ./Sports/valid_neg.dat -en ./Sports/test_neg.dat -m=test"
run steam_yelp steam  $R/steam  \
  bash -c "python main.py -tf ./Yelp/train.dat -vf ./Yelp/valid.dat -ef ./Yelp/test.dat \
           -vn ./Yelp/valid_neg.dat -en ./Yelp/test_neg.dat -m=train && \
           python main.py -tf ./Yelp/train.dat -vf ./Yelp/valid.dat -ef ./Yelp/test.dat \
           -vn ./Yelp/valid_neg.dat -en ./Yelp/test_neg.dat -m=valid && \
           python main.py -tf ./Yelp/train.dat -vf ./Yelp/valid.dat -ef ./Yelp/test.dat \
           -vn ./Yelp/valid_neg.dat -en ./Yelp/test_neg.dat -m=test"

# ── SEQUENTIAL TRACK: FMLP-Rec (~3 min per dataset) ──────────────────────────
say "=== FMLP-Rec sequential track ==="
run fmlp_beauty fmlp  $R/fmlp  python main.py --data_name=Beauty
run fmlp_sports fmlp  $R/fmlp  python main.py --data_name=Sports
run fmlp_yelp   fmlp  $R/fmlp  python main.py --data_name=Yelp

# ── SEQUENTIAL TRACK: PreferDiff (~5-7 min per dataset) ──────────────────────
# No --data_name arg in main.py; runs on its hardcoded default (Beauty).
say "=== PreferDiff sequential track ==="
run preferdiff_beauty preferdiff $R/preferdiff \
  python main.py --model=PreferDiff --sd=O --td=O --loss_type=cosine --lamda=0.4 --w=2 --hidden_size=3072 --ab=iids

say "=== RQ10 baseline runs complete ==="
echo ""
say "Summary (name  exit  minutes  peak_MiB):"
column -t "$RES/run_summary.tsv" 2>/dev/null || cat "$RES/run_summary.tsv"
