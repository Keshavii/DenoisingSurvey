#!/bin/bash
# DCF Wed. (1) Normal baseline inside DCF's own code: --drop_rate 0 --relabel_ratio 0 keeps every sample, so its loss is plain BCE
#     (settings only, no code change; checkpoint name differs by drop_rate). (2) Unchanged DCF repeat (seed hard-coded 2019): run-to-run spread.
source ~/miniconda3/etc/profile.d/conda.sh; conda activate dcf; cd ~/repos/DCF; export WANDB_MODE=disabled
run() { tag=$1; shift; echo "$(date '+%T') $tag"; rm -f ~/repos/loggg.log
  python -u main.py "$@" --gpu 0 > ~/partB_dcf/$tag.stderr 2>&1; mv ~/repos/loggg.log ~/partB_dcf/$tag.log
  echo "   $(grep -A2 'TEST' ~/partB_dcf/$tag.log | tail -2 | tr '\n' ' ')"; }
for ds in adressa yelp; do for model in GMF NeuMF-end; do run normal_${ds}_${model} --dataset $ds --model $model --drop_rate 0 --relabel_ratio 0; done; done
for ds in adressa yelp; do for model in GMF NeuMF-end; do run dcf_${ds}_${model}_rep2 --dataset $ds --model $model; done; done
echo "$(date '+%T') ALL DONE"
