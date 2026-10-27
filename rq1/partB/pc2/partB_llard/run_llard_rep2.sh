#!/bin/bash
# LLaRD: second unchanged run of the other 3 settings (seed hard-coded, but runs differ ~2%): report the spread (run rule for hard-coded seeds).
source ~/miniconda3/etc/profile.d/conda.sh; conda activate llard_r; cd ~/repos/LLaRD
for job in "amazon_book LGN" "yelp LGN" "amazon_book GMF"; do set -- $job
  python -u run_LLaRD.py --dataset $1 --model $2 --runid ${2}_2 > ~/partB_llard/llard_$1_$2_rep2.log 2>&1
  echo "$1 $2  first: $(grep 'Best Evaluation' ~/partB_llard/llard_$1_$2.log | tail -1 | cut -c17-)  rerun: $(grep 'Best Evaluation' ~/partB_llard/llard_$1_$2_rep2.log | tail -1 | cut -c17-)"
done; echo "ALL DONE"
