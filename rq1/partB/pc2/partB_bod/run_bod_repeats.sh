#!/bin/bash
# BOD repeats 2 and 3 (BOD sets no seed: each run is an independent repeat). Same official code, confs and edits as run_bod.sh.
# Waits while available RAM < 6 GB so DiffRec Amazon-Book (running in RAM) is never pushed into swap.
source ~/miniconda3/etc/profile.d/conda.sh; conda activate bod; cd ~/repos/BOD
for r in 2 3; do for ds in Beauty yelp2018 iFashion; do for m in BOD LightGCN; do
  out=~/partB_bod/${m}_${ds}_r$r.log
  if grep -q "^Running time" $out 2>/dev/null; then echo "skip $m $ds r$r"; continue; fi
  while [ $(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo) -lt 6 ]; do sleep 120; done
  sed -i "s#^training.set=.*#training.set=./dataset/$ds/train.txt#; s#^test.set=.*#test.set=./dataset/$ds/test.txt#" conf/$m.conf
  sed -i "s#^dataset.name=.*#dataset.name=$ds#" conf/$m.conf
  echo "$(date '+%F %T') start $m $ds r$r"
  echo $m | python -u main.py > $out 2>&1
  echo "$(date '+%F %T') end   $m $ds r$r   $(tail -6 $out | grep -E 'Recall|NDCG' | tr '\n' ' ')"
done; done; done
echo "ALL DONE"
