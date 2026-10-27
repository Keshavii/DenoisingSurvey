#!/bin/bash
# DDRM Part B: remaining 8 runs, authors' launchers unchanged, one at a time. Waits for the first run (LightGCN ML-1M).
while pgrep -f "^python -u train.py" > /dev/null; do sleep 60; done
source ~/miniconda3/etc/profile.d/conda.sh; conda activate ddrm
for job in "MF train.py" "SGL train.py" "LightGCN train_yelp.py" "MF train_yelp.py" "SGL train_yelp.py" "LightGCN train_amazon.py" "MF train_amazon.py" "SGL train_amazon.py"; do
  set -- $job; cd ~/repos/DDRM/DDRM_$1
  echo "$(date '+%F %T') start DDRM_$1 $2"
  python -u $2 > ~/partB_ddrm/launcher_$1_${2%.py}.log 2>&1
  echo "$(date '+%F %T') end   DDRM_$1 $2   $(grep -h -A1 '^Test:' $(ls -t log/*.txt | head -1) | tail -1 | cut -c1-120)"
done
echo "$(date '+%F %T') ALL DONE"
