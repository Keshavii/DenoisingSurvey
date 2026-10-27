#!/bin/bash
# DiffRec Amazon-Book, unmodified code, run alone; the dense matrix (~83 GB) spills to swap.
source ~/miniconda3/etc/profile.d/conda.sh; conda activate diffrec; cd ~/repos/DiffRec/DiffRec
echo "$(date '+%T') amazon-book_clean"
python -u main.py --cuda --dataset=amazon-book_clean --data_path=../datasets/amazon-book_clean/ --lr=5e-05 --weight_decay=0.0 --batch_size=400 --dims=[1000] --emb_size=10 --mean_type=x0 --steps=5 --noise_scale=0.0001 --noise_min=0.0005 --noise_max=0.005 --sampling_steps=0 --reweight=1 --log_name=log --round=1 --gpu=0 > ~/partB_diffrec/amazon-book_clean.log 2>&1
echo "$(date '+%T') amazon-book_noisy"
python -u main.py --cuda --dataset=amazon-book_noisy --data_path=../datasets/amazon-book_noisy/ --lr=5e-05 --weight_decay=0.0 --batch_size=400 --dims=[1000] --emb_size=10 --mean_type=x0 --steps=10 --noise_scale=0.005 --noise_min=0.0001 --noise_max=0.0005 --sampling_steps=0 --reweight=1 --log_name=log --round=1 --gpu=0 > ~/partB_diffrec/amazon-book_noisy.log 2>&1
echo "$(date '+%T') ALL DONE"
