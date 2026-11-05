#!/bin/bash
# DCF Part B: repository defaults (README gives none per dataset), unmodified code, seed hard-coded 2019.
source ~/miniconda3/etc/profile.d/conda.sh; conda activate dcf; cd ~/repos/DCF
export WANDB_MODE=disabled
for ds in adressa yelp; do for model in GMF NeuMF-end; do
  echo "$(date '+%T') DCF $ds $model"
  rm -f ~/repos/loggg.log
  python -u main.py --dataset $ds --model $model --gpu 0 > ~/partB_dcf/dcf_${ds}_${model}.stderr 2>&1
  mv ~/repos/loggg.log ~/partB_dcf/dcf_${ds}_${model}.log
  echo "   $(tail -3 ~/partB_dcf/dcf_${ds}_${model}.log | tr '\n' ' ')"
done; done
echo "$(date '+%T') ALL DONE"
