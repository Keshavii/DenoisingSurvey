#!/bin/bash
# Part B, DiffRec (SIGIR'23): the 6 released configurations (inference.py), official code, validation Recall@20 selection.
cd ~/repos/DiffRec/DiffRec
RUNS="
ml-1m_clean 0.001 [200,600] 40 0.005 0.005 0.01 1
ml-1m_noisy 0.001 [200,600] 5 0.5 0.001 0.01 0
yelp_clean 1e-05 [1000] 5 0.01 0.001 0.01 1
yelp_noisy 1e-05 [1000] 5 0.001 0.0005 0.01 0
amazon-book_clean 5e-05 [1000] 5 0.0001 0.0005 0.005 1
amazon-book_noisy 5e-05 [1000] 10 0.005 0.0001 0.0005 1
"
echo "$RUNS" | while read ds lr dims steps scale nmin nmax rw; do
  [ -z "$ds" ] && continue
  out=~/partB_diffrec/$ds.log
  if grep -q "^End. Best Epoch" $out 2>/dev/null; then echo "skip $ds"; continue; fi
  echo "$(date '+%F %T') start $ds"
  python -u main.py --cuda --dataset=$ds --data_path=../datasets/$ds/ --lr=$lr --weight_decay=0.0 --batch_size=400 \
    --dims=$dims --emb_size=10 --mean_type=x0 --steps=$steps --noise_scale=$scale --noise_min=$nmin --noise_max=$nmax \
    --sampling_steps=0 --reweight=$rw --log_name=log --round=1 --gpu=0 > $out 2>&1
  echo "$(date '+%F %T') end   $ds  $(grep -A3 '^End. Best Epoch' $out | tr '\n' ' ' | cut -c1-200)"
done
echo "ALL DONE"
