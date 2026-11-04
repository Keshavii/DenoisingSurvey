#!/bin/bash
# RQ10 real runs — PC3 (RTX 4090): baseline reproductions on each method's home datasets.
# These establish per-method baselines on clean data for RQ10 (specialist performance).
# Runs the methods that passed smoke tests; each job is resumable via .done files.
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
# seed fixed at 2023 in run_GBSR.py; each call is one independent run
# datasets in repo: douban_book, epinions, yelp
say "=== GBSR social track ==="
run gbsr_douban   gbsr  $R/gbsr/torch_version  python run_GBSR.py --dataset douban_book --runid run1 --beta 40 --sigma 2.5
run gbsr_epinions gbsr  $R/gbsr/torch_version  python run_GBSR.py --dataset epinions    --runid run1 --beta 40 --sigma 2.5
run gbsr_yelp     gbsr  $R/gbsr/torch_version  python run_GBSR.py --dataset yelp        --runid run1 --beta 40 --sigma 2.5
# Second pass (different runid = different random tie assignment; seed still fixed)
run gbsr_douban_r2  gbsr $R/gbsr/torch_version python run_GBSR.py --dataset douban_book --runid run2 --beta 40 --sigma 2.5
run gbsr_epinions_r2 gbsr $R/gbsr/torch_version python run_GBSR.py --dataset epinions  --runid run2 --beta 40 --sigma 2.5
run gbsr_yelp_r2    gbsr $R/gbsr/torch_version python run_GBSR.py --dataset yelp       --runid run2 --beta 40 --sigma 2.5

# ── SEQUENTIAL TRACK: STEAM (~128 min per dataset, 23 GB peak) ───────────────
# repo ships Beauty, Sports, Yelp; uses internal config — dataset arg TBD
say "=== STEAM sequential track ==="
run steam_beauty steam  $R/steam  bash -c "python main.py -m=train && python main.py -m=valid && python main.py -m=test"
# Sports and Yelp: try --data_name (most common SASRec-style arg); skip if unknown
# Update this script once the CLI is confirmed with:
#   python main.py --help 2>&1 | grep -i data
run steam_sports steam  $R/steam  bash -c "python main.py --data_name=Sports -m=train && python main.py --data_name=Sports -m=valid && python main.py --data_name=Sports -m=test"
run steam_yelp   steam  $R/steam  bash -c "python main.py --data_name=Yelp   -m=train && python main.py --data_name=Yelp   -m=valid && python main.py --data_name=Yelp   -m=test"

# ── SEQUENTIAL TRACK: FMLP-Rec (~3 min on Beauty) ────────────────────────────
say "=== FMLP-Rec sequential track ==="
run fmlp_beauty fmlp  $R/fmlp  python main.py --data_name=Beauty
run fmlp_sports fmlp  $R/fmlp  python main.py --data_name=Sports
run fmlp_yelp   fmlp  $R/fmlp  python main.py --data_name=Yelp

# ── SEQUENTIAL TRACK: PreferDiff (~5 min, default = Beauty) ──────────────────
# repo ships Beauty, Sports, Toys, CDs; dataset arg TBD (try --data_name)
say "=== PreferDiff sequential track ==="
run preferdiff_beauty preferdiff $R/preferdiff \
  python main.py --model=PreferDiff --sd=O --td=O --loss_type=cosine --lamda=0.4 --w=2 --hidden_size=3072 --ab=iids
run preferdiff_sports preferdiff $R/preferdiff \
  python main.py --model=PreferDiff --sd=O --td=O --loss_type=cosine --lamda=0.4 --w=2 --hidden_size=3072 --ab=iids --data_name=Sports
run preferdiff_toys   preferdiff $R/preferdiff \
  python main.py --model=PreferDiff --sd=O --td=O --loss_type=cosine --lamda=0.4 --w=2 --hidden_size=3072 --ab=iids --data_name=Toys
run preferdiff_cds    preferdiff $R/preferdiff \
  python main.py --model=PreferDiff --sd=O --td=O --loss_type=cosine --lamda=0.4 --w=2 --hidden_size=3072 --ab=iids --data_name=CDs

say "=== RQ10 baseline runs complete ==="
echo ""
say "Summary (name  exit  minutes  peak_MiB):"
column -t "$RES/run_summary.tsv" 2>/dev/null || cat "$RES/run_summary.tsv"
