#!/bin/bash
# Part B, ADT (T-CE / R-CE, WSDM'21): the authors' 18 released configurations, their own code and settings.
# Usage: run_adt.sh <dataset>   (yelp | adressa | amazon_book). Logs go to mylog_rep2/; finished runs are skipped.
cd ~/repos/DenoisingRec
ONLY=$1
RUNS="
yelp GMF T 0 0
yelp GMF T 0.1 30000
yelp GMF R 0.2
yelp NeuMF-end T 0 0
yelp NeuMF-end T 0.2 30000
yelp NeuMF-end R 0.2
adressa GMF T 0 0
adressa GMF T 0.05 30000
adressa GMF R 0.2
adressa NeuMF-end T 0 0
adressa NeuMF-end T 0.2 1000
adressa NeuMF-end R 0.25
amazon_book GMF T 0 0
amazon_book GMF T 0.1 30000
amazon_book GMF R 0.3
amazon_book NeuMF-end T 0 0
amazon_book NeuMF-end T 0.2 30000
amazon_book NeuMF-end R 0.25
"
echo "$RUNS" | while read ds model kind a b; do
  [ -z "$ds" ] && continue
  [ -n "$ONLY" ] && [ "$ds" != "$ONLY" ] && continue
  if [ "$kind" = T ]; then dir=T_CE; name="${model}_${a}-${b}"; args="--drop_rate=$a --num_gradual=$b"
  else dir=R_CE; name="${model}_${a}"; args="--alpha=$a"; fi
  mkdir -p $dir/mylog_rep2/$ds $dir/models/$ds
  log=$dir/mylog_rep2/$ds/$name.log
  if grep -q "^NDCG" $log 2>/dev/null; then echo "skip $dir $ds $name (done)"; continue; fi
  echo "$(date '+%F %T') start $dir $ds $name"
  start=$(date +%s)
  (cd $dir && python -u main.py --dataset=$ds --model=$model $args --gpu=0 > mylog_rep2/$ds/$name.log 2>&1)
  echo "$(date '+%F %T') end   $dir $ds $name  ($(( ($(date +%s)-start)/60 )) min)  $(grep '^NDCG' $log)"
done
echo "ALL DONE $ONLY"
