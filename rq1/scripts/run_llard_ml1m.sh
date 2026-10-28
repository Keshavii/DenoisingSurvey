#!/bin/bash
# LLaRD knowledge for ML-1M on PC 2: items once, then one build per training file (N0 and 3 injected-noise seeds).
# Resume: stages are cheap to rerun, finished builds are skipped. Progress: $LOG
#   systemd-run --user --unit=llard-ml1m --collect bash -c "bash ~/rq1-kit/scripts/run_llard_ml1m.sh > ~/llard_ml1m.log 2>&1"
set -u
source ~/miniconda3/etc/profile.d/conda.sh && conda activate vllm
export VLLM_USE_FLASHINFER_SAMPLER=0
KIT=${KIT:-$HOME/rq1-kit}; DATA=${DATA:-$HOME/rq1-data/ml1m}; RAW=${RAW:-$HOME/rq1-data/ml-1m}
OUT=${OUT:-$DATA/llard}; LOG=${LOG:-$HOME/llard_progress.log}
ARGS="--data $DATA --raw $RAW --prompts $HOME/repos/LLaRD/system_prompt --out $OUT --model $HOME/models/Llama-3.1-8B-Instruct"
cd $KIT
python -c "import pandas, scipy, sentence_transformers" 2>/dev/null || pip install -q pandas scipy sentence-transformers
step() { echo "$(date '+%F %T') start $*" >> $LOG; python -m rq1kit.llard_knowledge "$@" $ARGS >> $LOG.detail 2>&1 && echo "$(date '+%F %T') end   $*" >> $LOG || { echo "$(date '+%F %T') FAIL  $*" >> $LOG; exit 1; }; }
[ -f $OUT/items/itm_attrs.json ] || step --stage items
for B in N0 N2_20_s1 N2_20_s2 N2_20_s3; do
  F=train.tsv; [ $B != N0 ] && F=train_${B%_s*}_s${B##*_s}.tsv
  [ -f $OUT/$B/prf_k/usr_emb_np.pkl ] && [ -f $OUT/$B/rel_k/uu_data.npy ] && continue
  step --stage users --build $B --train_file $F
  step --stage knowledge --build $B --train_file $F
  step --stage embed --build $B
done
echo "$(date '+%F %T') ALL DONE" >> $LOG
