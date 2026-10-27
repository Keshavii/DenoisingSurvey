#!/bin/bash
# DCF on README versions (torch 1.10.0+cu111 (README says 1.8.1, but the code calls torch.concat, added in 1.10; 1.10.0 is the closest version that runs it), numpy 1.19.5, scikit-learn 0.24.2): DCF and Normal (--drop_rate 0 --relabel_ratio 0), Adressa and Yelp, GMF and NeuMF.
# Waits for PC 1's night queue (PLD LightGCN, swap job) to finish first.
while pgrep -f "run_pc1_night.sh" > /dev/null; do sleep 120; done
source ~/miniconda3/etc/profile.d/conda.sh; conda activate dcf18; cd ~/repos/DCF; export WANDB_MODE=disabled; O=~/partB_dcf/t18
run() { tag=$1; shift; echo "$(date '+%F %T') $tag"; rm -f ~/repos/loggg.log
  python -u main.py "$@" --gpu 0 > $O/$tag.stderr 2>&1; mv ~/repos/loggg.log $O/$tag.log
  echo "   $(grep -A2 'TEST' $O/$tag.log | tail -2 | tr '\n' ' ')"; }
for ds in adressa yelp; do for model in GMF NeuMF-end; do
  run dcf_${ds}_${model} --dataset $ds --model $model
  run normal_${ds}_${model} --dataset $ds --model $model --drop_rate 0 --relabel_ratio 0
done; done
echo "$(date '+%F %T') ALL DONE"
