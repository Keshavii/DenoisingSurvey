#!/bin/bash
# Part B, BOD (KDD'23): BOD and its own plain LightGCN ("Normal"), official code and confs, per dataset.
cd ~/repos/BOD
for ds in Beauty yelp2018 iFashion; do
  for m in BOD LightGCN; do
    out=~/partB_bod/${m}_${ds}.log
    if grep -q "Running time" $out 2>/dev/null; then echo "skip $m $ds"; continue; fi
    sed -i "s#^training.set=.*#training.set=./dataset/$ds/train.txt#; s#^test.set=.*#test.set=./dataset/$ds/test.txt#" conf/$m.conf
    sed -i "s#^dataset.name=.*#dataset.name=$ds#" conf/$m.conf
    echo "$(date '+%F %T') start $m $ds"
    echo $m | python -u main.py > $out 2>&1
    echo "$(date '+%F %T') end   $m $ds"
  done
done
echo "ALL DONE"
