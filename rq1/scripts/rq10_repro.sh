#!/bin/bash
# RQ10 smoke reproductions on PC3: each specialist's README command, unchanged, on the home data its repository
# ships. Purpose: the code runs on the 4090 in its env, and the real run time and peak GPU memory for planning.
# Waits for rq10_setup.sh to finish. Each run has a time limit; a failure is logged and the queue moves on.
#   systemd-run --user --unit=rq10repro --collect bash -c "bash ~/survey/rq1/scripts/rq10_repro.sh > ~/rq10_repro.log 2>&1"
# Summary: cat ~/survey/rq10/logs/repro_summary.tsv   (name, exit code, minutes, peak GPU MiB)
set -u
ROOT=${ROOT:-$HOME/survey/rq10}
R=$ROOT/repos
L=$ROOT/logs
LIMIT=${LIMIT:-3h}
mkdir -p "$L"
say() { echo "$(date '+%F %T') $*"; }

say "waiting for rq10setup to finish"; rm -f $L/repro_summary.tsv.tmp
while systemctl --user is-active --quiet rq10setup; do sleep 60; done
say "setup finished; envs ready: $(ls $ROOT/envs_ok 2>/dev/null | tr '\n' ' ')"

run() {  # name env dir command...
  local n=$1 env=$2 dir=$3; shift 3
  [ -f "$L/repro_$n.done" ] && { say "$n: done before"; return; }
  [ -f "$ROOT/envs_ok/$env" ] || { say "$n: env $env missing, skipped"; printf "%s\tno-env\t0\t0\n" $n >> $L/repro_summary.tsv; return; }
  say "$n: start ($*)"
  local peak=$L/repro_$n.gpu t0=$(date +%s)
  ( while true; do nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits; sleep 5; done ) > $peak &
  local mon=$!
  (cd "$dir" && PATH=~/miniconda3/envs/r10-$env/bin:$PATH LD_LIBRARY_PATH=~/miniconda3/envs/r10-$env/lib timeout $LIMIT "$@") \
    > "$L/repro_$n.log" 2>&1
  local rc=$?
  kill $mon 2>/dev/null
  local mins=$(( ($(date +%s) - t0) / 60 )) mib=$(sort -n $peak | tail -1)
  printf "%s\t%s\t%s\t%s\n" $n $rc $mins "${mib:-0}" >> $L/repro_summary.tsv
  [ $rc -eq 0 ] && touch "$L/repro_$n.done"
  say "$n: exit $rc after $mins min, peak GPU $mib MiB (124 = time limit)"
}

# README commands, verbatim (first dataset each README shows)
run gbsr    gbsr       $R/gbsr/torch_version python run_GBSR.py --dataset douban_book --runid 40+2.5sigma --beta 40 --sigma 2.5
# HDSR: run_HDSR.py sets dataset and device in code (README: edit them); device 'cuda:1' does not exist on PC3, so a
# copy with only that line set to cuda:0 is run (recorded deviation; the repository file stays unchanged)
sed "s/config\['device'\] = 'cuda:1'/config['device'] = 'cuda:0'/" $R/hdsr/src/run_HDSR.py > $R/hdsr/src/run_HDSR_pc3.py
run hdsr    hdsr       $R/hdsr/src           python run_HDSR_pc3.py
run gdmsr   gdmsr      $R/gdmsr              bash run.sh
run steam   steam      $R/steam              bash -c "python main.py -m=train && python main.py -m=valid && python main.py -m=test"
run fmlp    fmlp       $R/fmlp               python main.py --data_name=Beauty
run preferdiff preferdiff $R/preferdiff      python main.py --model=PreferDiff --sd=O --td=O --loss_type=cosine --lamda=0.4 --w=2 --hidden_size=3072 --ab=iids
say "RQ10 smoke reproductions finished"
column -t $L/repro_summary.tsv 2>/dev/null || cat $L/repro_summary.tsv
