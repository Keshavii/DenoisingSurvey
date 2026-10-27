#!/bin/bash
# DDRM Amazon-Book seeds, continued. Waits for the running SGL seed-2021 run. LightGCN with --testbatch=128 (its evaluation needs 21.75 GB at the default 512;
# evaluation batch only). SGL keeps the launcher default (it fits).
while pgrep -f "main.py.*log_seed2021.*seed=2021" > /dev/null; do sleep 60; done
echo "   SGL seed 2021: $(grep -A1 '^Test:' ~/partB_ddrm/sgl_amazon_s2021.log | tail -1 | cut -c1-120)"
source ~/miniconda3/etc/profile.d/conda.sh; conda activate ddrm_r
for s in 2021 2022; do
  cd ~/repos/DDRM/DDRM_LightGCN; echo "$(date '+%F %T') DDRM LightGCN amazon seed $s (testbatch 128)"
  python -u main.py --load=1 --act=relu --beta=0 --dataset=amazon-book --data_path=../data/amazon-book --lr=1e-05 --diff_lr=0.001 --layer=2 --alpha=0.5 --steps=50 --epochs=1000 --sampling_steps=62 --noise_scale=0.01 --noise_min=0.0001 --noise_max=0.001 --dims=[200,1000] --log_name=log_seed$s --gpu=0 --seed=$s --testbatch=128 > ~/partB_ddrm/lgn_amazon_s$s.log 2>&1
  echo "   $(grep -m1 '>>SEED' ~/partB_ddrm/lgn_amazon_s$s.log) $(grep -A1 '^Test:' ~/partB_ddrm/lgn_amazon_s$s.log | tail -1 | cut -c1-120)"
done
cd ~/repos/DDRM/DDRM_SGL; echo "$(date '+%F %T') DDRM SGL amazon seed 2022"
python -u main.py --load=1 --act=sigmoid --beta=0.5 --dataset=amazon-book --data_path=../data/amazon-book --lr=1e-05 --diff_lr=0.001 --layer=2 --alpha=0.6 --steps=3 --epochs=1000 --sampling_steps=3 --noise_scale=0.0001 --noise_min=0.0001 --noise_max=0.001 --dims=[300,1000] --log_name=log_seed2022 --gpu=0 --seed=2022 > ~/partB_ddrm/sgl_amazon_s2022.log 2>&1
echo "   $(grep -m1 '>>SEED' ~/partB_ddrm/sgl_amazon_s2022.log) $(grep -A1 '^Test:' ~/partB_ddrm/sgl_amazon_s2022.log | tail -1 | cut -c1-120)"
echo "$(date '+%F %T') ALL DONE"
