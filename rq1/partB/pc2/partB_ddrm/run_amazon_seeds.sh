#!/bin/bash
# (1) LLaRD determinism check: Yelp GMF rerun unchanged (seed hard-coded). (2) DDRM Amazon-Book LightGCN and SGL, seeds 2021, 2022 (borderline vs paper):
#     launcher settings from train_amazon.py plus --seed (CLI), env ddrm_r.
source ~/miniconda3/etc/profile.d/conda.sh
conda activate llard_r; cd ~/repos/LLaRD
echo "$(date '+%F %T') LLaRD yelp GMF rerun"; python -u run_LLaRD.py --dataset yelp --model GMF --runid GMF_2 > ~/partB_llard/llard_yelp_GMF_rep2.log 2>&1
echo "   first: $(grep 'Best Evaluation' ~/partB_llard/llard_yelp_GMF.log | tail -1)"; echo "   rerun: $(grep 'Best Evaluation' ~/partB_llard/llard_yelp_GMF_rep2.log | tail -1)"
conda activate ddrm_r
for s in 2021 2022; do
  cd ~/repos/DDRM/DDRM_LightGCN; echo "$(date '+%F %T') DDRM LightGCN amazon seed $s"
  python -u main.py --load=1 --act=relu --beta=0 --dataset=amazon-book --data_path=../data/amazon-book --lr=1e-05 --diff_lr=0.001 --layer=2 --alpha=0.5 --steps=50 --epochs=1000 --sampling_steps=62 --noise_scale=0.01 --noise_min=0.0001 --noise_max=0.001 --dims=[200,1000] --log_name=log_seed$s --gpu=0 --seed=$s > ~/partB_ddrm/lgn_amazon_s$s.log 2>&1
  echo "   $(grep -m1 '>>SEED' ~/partB_ddrm/lgn_amazon_s$s.log) $(grep -A1 '^Test:' ~/partB_ddrm/lgn_amazon_s$s.log | tail -1 | cut -c1-120)"
  cd ~/repos/DDRM/DDRM_SGL; echo "$(date '+%F %T') DDRM SGL amazon seed $s"
  python -u main.py --load=1 --act=sigmoid --beta=0.5 --dataset=amazon-book --data_path=../data/amazon-book --lr=1e-05 --diff_lr=0.001 --layer=2 --alpha=0.6 --steps=3 --epochs=1000 --sampling_steps=3 --noise_scale=0.0001 --noise_min=0.0001 --noise_max=0.001 --dims=[300,1000] --log_name=log_seed$s --gpu=0 --seed=$s > ~/partB_ddrm/sgl_amazon_s$s.log 2>&1
  echo "   $(grep -m1 '>>SEED' ~/partB_ddrm/sgl_amazon_s$s.log) $(grep -A1 '^Test:' ~/partB_ddrm/sgl_amazon_s$s.log | tail -1 | cut -c1-120)"
done; echo "$(date '+%F %T') ALL DONE"
