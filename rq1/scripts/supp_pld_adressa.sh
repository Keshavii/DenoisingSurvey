#!/bin/bash
# Supplement to Part C (not part of the protocol): PLD on Adressa with --begin_adv 0.
# Why: with the authors' default begin_adv 5 the best clean-validation epoch on Adressa is epoch 1, so PLD never starts
# resampling and its result equals Plain-BPR exactly. Here resampling starts at epoch 0. Tuned item_num 5, temp 0.01
# (the Part C pick); everything else as in the Part C final. Results go to results/supp/, never to results/C/.
#   cd ~/survey/rq1 && bash scripts/supp_pld_adressa.sh
set -u
cd "$(dirname "$0")/.."
for S in 1 2 3; do
  for C in N0 N2_20; do
    TF=train.tsv; [ $C != N0 ] && TF=train_${C}_s${S}.tsv
    RD=runs/adressa/pldb0_lightgcn_${C}_s${S}; RES=results/supp/adressa/pldb0_lightgcn_${C}_s${S}.json
    [ -f $RES ] && continue
    python -m rq1kit.pld --begin_adv 0 --item_num 5 --temp 0.01 --data data/adressa --train_file $TF --model lightgcn \
      --lr 0.001 --reg 0.01 --seed $S --run_dir $RD && \
    python -m rq1kit.evaluate --data data/adressa --train_file $TF --topk $RD/topk_test.npy --out $RES \
      --tag part=supp dataset=adressa method=PLD-begin0 backbone=LightGCN cond=$C seed=$S train_file=$TF
  done
done
echo done
