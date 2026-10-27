#!/bin/bash
# Part B, DeCA (WWW'22): GMF and NeuMF-end on ml-100k, modcloth, adressa; Normal, DeCA, DeCA(p); repository --default settings.
cd ~/repos/DeCA
mkdir -p output                 # missing folder in a fresh clone (audit 2.8)
for ds in ml-100k modcloth adressa; do
  for model in GMF NeuMF-end; do
    for method in Normal DeCA DeCAp; do
      out=~/partB_deca/${ds}_${model}_${method}.log
      if grep -q "CLEAN TEST" $out 2>/dev/null; then echo "skip $ds $model $method"; continue; fi
      m=""; [ "$method" != "Normal" ] && m="--method $method"
      echo "$(date '+%F %T') start $ds $model $method"
      python -u main.py --model $model --dataset $ds $m --default > $out 2>&1
      echo "$(date '+%F %T') end   $ds $model $method  $(grep -A2 'CLEAN TEST' $out | tr '\n' ' ' | cut -c1-160)"
    done
  done
done
echo "ALL DONE"
