#!/bin/bash
# Tue 20 Oct, PC 1 side jobs: DeCA Electronics (GMF, NeuMF; Normal, DeCA, DeCA(p)), then SGL iFashion.
source ~/miniconda3/etc/profile.d/conda.sh; O=~/partB_today
conda activate deca; cd ~/repos/DeCA; mkdir -p output
for model in GMF NeuMF-end; do for m in Normal DeCA DeCAp; do a=""; [ $m != Normal ] && a="--method $m"
  echo "$(date '+%T') DeCA electronics $model $m"; python -u main.py --model $model --dataset electronics $a --default > $O/deca_electronics_${model}_$m.log 2>&1
  echo "   $(grep -A1 'CLEAN TEST' $O/deca_electronics_${model}_$m.log | tail -1)"
done; done
conda activate sgl; cd ~/repos/SGL-Torch
echo "$(date '+%T') SGL ifashion"
python main.py --recommender=SGL --dataset=ifashion --aug_type=ED --reg=1e-3 --n_layers=3 --ssl_reg=0.02 --ssl_ratio=0.4 --ssl_temp=0.5 > $O/sgl_ifashion.log 2>&1
grep -A2 "best_result" $O/sgl_ifashion.log | tail -1
echo "$(date '+%T') ALL DONE"
