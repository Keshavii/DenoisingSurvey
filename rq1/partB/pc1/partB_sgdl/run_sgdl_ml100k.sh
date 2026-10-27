#!/bin/bash
# SGDL ML-100K: shipped data, README command (batch 128), unmodified code, seed 2020. Waits for the Adressa/Yelp attempts to end.
while pgrep -f "run_sgdl_alone.sh" > /dev/null; do sleep 60; done
source ~/miniconda3/etc/profile.d/conda.sh; conda activate sgdl; cd ~/repos/SGDL/code; mkdir -p ml100k
nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -l 2 > ~/partB_sgdl/gpu_mem_ml100k.log & MON=$!
echo "$(date '+%T') SGDL ml100k"
python -u main.py --batch_size 128 --lr 0.0005 --meta_lr 0.0005 --model lgn --eval_freq 5 --stop_step 8 --dataset ml100k > ~/partB_sgdl/sgdl_ml100k.log 2>&1
kill $MON; echo "   $(grep -E "recall|OutOfMemory" ~/partB_sgdl/sgdl_ml100k.log | tail -1 | cut -c1-160)"; echo "peak GPU MiB: $(sort -n ~/partB_sgdl/gpu_mem_ml100k.log | tail -1)"
echo "$(date '+%T') ALL DONE"
