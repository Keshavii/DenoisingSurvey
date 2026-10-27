#!/bin/bash
# DDRM LightGCN ML-1M (borderline at Recall@10): seeds 2021, 2022. Same command as the authors' launcher (train.py), plus --seed (CLI).
source ~/miniconda3/etc/profile.d/conda.sh; conda activate ddrm; cd ~/repos/DDRM/DDRM_LightGCN
for s in 2021 2022; do
  echo "$(date '+%T') seed $s"
  python -u main.py --load=1 --act=relu --beta=0 --dataset=ml-1m --data_path=../data/ml-1m --lr=1e-05 --diff_lr=0.001 --layer=2 --alpha=0.1 --steps=50 --epochs=1000 --sampling_steps=62 --noise_scale=0.01 --noise_min=0.0001 --noise_max=0.001 --dims=[200,1100] --log_name=log_seed$s --gpu=0 --seed=$s > ~/partB_ddrm/lightgcn_ml1m_s$s.log 2>&1
  echo "   $(grep -m1 '>>SEED' ~/partB_ddrm/lightgcn_ml1m_s$s.log) $(grep -A1 '^Test:' ~/partB_ddrm/lightgcn_ml1m_s$s.log | tail -1 | cut -c1-120)"
done
echo "$(date '+%T') ALL DONE"
