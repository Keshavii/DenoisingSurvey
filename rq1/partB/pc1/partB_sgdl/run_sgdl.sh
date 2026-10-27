#!/bin/bash
# SGDL Part B, README commands (LightGCN), unmodified code, seed 2020 (CLI default). Data: DenoisingRec Adressa and Yelp, linked into SGDL/data.
source ~/miniconda3/etc/profile.d/conda.sh; conda activate sgdl; cd ~/repos/SGDL/code
echo "$(date '+%T') SGDL adressa"
python -u main.py --batch_size 1024 --lr 0.0005 --meta_lr 0.0005 --model lgn --eval_freq 10 --stop_step 4 --dataset adressa > ~/partB_sgdl/sgdl_adressa.log 2>&1
echo "   $(grep -i "recall" ~/partB_sgdl/sgdl_adressa.log | tail -1)"
echo "$(date '+%T') SGDL yelp"
python -u main.py --batch_size 2048 --lr 0.0005 --meta_lr 0.0005 --model lgn --eval_freq 10 --stop_step 4 --dataset yelp > ~/partB_sgdl/sgdl_yelp.log 2>&1
echo "   $(grep -i "recall" ~/partB_sgdl/sgdl_yelp.log | tail -1)"
echo "$(date '+%T') ALL DONE"
