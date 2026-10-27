#!/bin/bash
# PC 1, Wed night, one job at a time.
# 1) SGDL ML-100K, README PyTorch 1.4 (pinned env sgdl14; newer PyTorch rejects its meta-step), README command, no code change.
# 2) SGDL Adressa, same pinned env, README command: one retry (it ran out of GPU memory on newer PyTorch).
# 3) PLD with its own LightGCN (Gowalla, Yelp x Origin, PLD), alone with swap.
source ~/miniconda3/etc/profile.d/conda.sh
conda activate sgdl14; cd ~/repos/SGDL/code; O=~/partB_sgdl
nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -l 2 > $O/gpu_mem_t14.log & MON=$!
echo "$(date '+%F %T') SGDL ml100k (torch 1.4)"
python -u main.py --batch_size 128 --lr 0.0005 --meta_lr 0.0005 --model lgn --eval_freq 5 --stop_step 8 --dataset ml100k > $O/sgdl_ml100k_t14.log 2>&1
echo "   $(grep -E "recall|Error" $O/sgdl_ml100k_t14.log | tail -1 | cut -c1-160)"
echo "$(date '+%F %T') SGDL adressa (torch 1.4)"
python -u main.py --batch_size 1024 --lr 0.0005 --meta_lr 0.0005 --model lgn --eval_freq 10 --stop_step 4 --dataset adressa > $O/sgdl_adressa_t14.log 2>&1
echo "   $(grep -E "recall|out of memory|Error" $O/sgdl_adressa_t14.log | tail -1 | cut -c1-160)"
kill $MON; echo "   peak GPU MiB: $(sort -n $O/gpu_mem_t14.log | tail -1)"
conda activate pld; cd ~/repos/PLD
for ds in Gowalla Yelp; do for m in Origin PLD; do
  echo "$(date '+%F %T') PLD $ds LightGCN $m"
  python main.py --model=LightGCN --method=$m --dataset=$ds --device_id=0 > ~/partB_pld/${ds}_LightGCN_${m}.log 2>&1
  echo "   $(grep -E "Recall@20" ~/partB_pld/${ds}_LightGCN_${m}.log | tail -1)"
done; done
echo "$(date '+%F %T') ALL DONE"
