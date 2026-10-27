#!/bin/bash
# LLaRD Part B, README versions (env llard_r): Yelp LightGCN, then GMF on Amazon-Book and Yelp. Code defaults otherwise (README gives no per-dataset values).
source ~/miniconda3/etc/profile.d/conda.sh; conda activate llard_r; cd ~/repos/LLaRD
for job in "yelp LGN" "amazon_book GMF" "yelp GMF"; do set -- $job
  echo "$(date '+%F %T') start $1 $2"
  python -u run_LLaRD.py --dataset $1 --model $2 --runid ${2}_1 > ~/partB_llard/llard_$1_$2.log 2>&1
  echo "$(date '+%F %T') end   $1 $2   $(grep 'Best Evaluation' ~/partB_llard/llard_$1_$2.log | tail -1)"
done; echo "$(date '+%F %T') ALL DONE"
