#!/bin/bash
# SGDL rerun ALONE on the GPU (ladder step 1) with PyTorch's expandable-segments allocator (environment setting, no code change).
# If a dataset still runs out of GPU memory: one retry with the exposed --A_split option (graph matmul in folds, same maths; ladder step 3).
source ~/miniconda3/etc/profile.d/conda.sh; conda activate sgdl; cd ~/repos/SGDL/code
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True; O=~/partB_sgdl
nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -l 5 > $O/gpu_mem.log & MON=$!
for ds in adressa yelp; do
  [ $ds = adressa ] && bs=1024 || bs=2048
  for try in alone split; do
    extra=""; [ $try = split ] && extra="--A_split True"
    echo "$(date '+%T') SGDL $ds ($try)"
    python -u main.py --batch_size $bs --lr 0.0005 --meta_lr 0.0005 --model lgn --eval_freq 10 --stop_step 4 --dataset $ds $extra > $O/sgdl_${ds}_$try.log 2>&1
    if grep -q "OutOfMemoryError" $O/sgdl_${ds}_$try.log; then echo "   out of GPU memory"; else echo "   $(tail -3 $O/sgdl_${ds}_$try.log | tr '\n' ' ')"; break; fi
  done
done
kill $MON; echo "peak GPU MiB: $(sort -n $O/gpu_mem.log | tail -1)"; echo "$(date '+%T') ALL DONE"
