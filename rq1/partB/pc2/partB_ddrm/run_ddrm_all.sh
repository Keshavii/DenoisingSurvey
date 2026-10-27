#!/bin/bash
# DDRM Part B on closest working versions (Python 3.8, numpy 1.21.2; PyTorch 1.7.0 fails: cuSPARSE of CUDA 11.0 not supported on RTX 4090): all 9 launchers unchanged, then LightGCN ML-1M seeds 2021, 2022.
source ~/miniconda3/etc/profile.d/conda.sh; conda activate ddrm_r
for job in "LightGCN train.py" "MF train.py" "SGL train.py" "LightGCN train_yelp.py" "MF train_yelp.py" "SGL train_yelp.py" "LightGCN train_amazon.py" "MF train_amazon.py" "SGL train_amazon.py"; do
  set -- $job; cd ~/repos/DDRM/DDRM_$1
  echo "$(date '+%F %T') start DDRM_$1 $2"
  python -u $2 > ~/partB_ddrm/t17_launcher_$1_${2%.py}.log 2>&1
  echo "$(date '+%F %T') end   DDRM_$1 $2   $(grep -h -A1 '^Test:' $(ls -t log/*.txt | head -1) | tail -1 | cut -c1-120)"
done
cd ~/repos/DDRM/DDRM_LightGCN
for s in 2021 2022; do echo "$(date '+%F %T') LightGCN ml-1m seed $s"
  python -u main.py --load=1 --act=relu --beta=0 --dataset=ml-1m --data_path=../data/ml-1m --lr=1e-05 --diff_lr=0.001 --layer=2 --alpha=0.1 --steps=50 --epochs=1000 --sampling_steps=62 --noise_scale=0.01 --noise_min=0.0001 --noise_max=0.001 --dims=[200,1100] --log_name=log_seed$s --gpu=0 --seed=$s > ~/partB_ddrm/t17_lightgcn_ml1m_s$s.log 2>&1
  echo "   $(grep -A1 '^Test:' ~/partB_ddrm/t17_lightgcn_ml1m_s$s.log | tail -1 | cut -c1-120)"; done
echo "$(date '+%F %T') ALL DONE"
