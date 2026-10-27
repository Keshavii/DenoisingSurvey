#!/bin/bash
# Defensibility runs on PC 1 (Mon 19 Oct night): seeds for RGCF, DeCA, SGL; DeCA Modcloth GMF with embedding 64.
source ~/miniconda3/etc/profile.d/conda.sh
O=~/partB_extra
conda activate deca
cd ~/repos/DeCA_e64 && mkdir -p output
for m in Normal DeCA DeCAp; do a=""; [ $m != Normal ] && a="--method $m"
  echo "$(date '+%T') DeCA e64 modcloth GMF $m"; python -u main.py --model GMF --dataset modcloth $a --default --factor_num 64 > $O/deca_e64_modcloth_GMF_$m.log 2>&1; done
cd ~/repos/DeCA && mkdir -p output
for s in 2021 2022; do for ds in ml-100k modcloth adressa; do for m in Normal DeCA DeCAp; do a=""; [ $m != Normal ] && a="--method $m"
  echo "$(date '+%T') DeCA $ds GMF $m seed $s"; python -u main.py --model GMF --dataset $ds $a --default --seed $s > $O/deca_${ds}_GMF_${m}_s$s.log 2>&1
done; done; done
conda activate rgcf
cd ~/repos/RGCF
for s in 2021 2022; do for p in None replace; do
  echo "$(date '+%T') RGCF ml-1m $p seed $s"; python -u run_rgcf.py --ptb_strategy=$p --seed=$s > $O/rgcf_ml1m_${p}_s$s.log 2>&1
done; done
conda activate sgl
cd ~/repos/SGL-Torch
for s in 2022 2023; do
  echo "$(date '+%T') SGL yelp2018 seed $s"; python main.py --recommender=SGL --dataset=yelp2018 --aug_type=ED --reg=1e-4 --n_layers=3 --ssl_reg=0.1 --ssl_ratio=0.1 --ssl_temp=0.2 --seed=$s > $O/sgl_yelp2018_s$s.log 2>&1
done
echo "$(date '+%T') ALL DONE"
