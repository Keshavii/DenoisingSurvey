#!/bin/bash
# Waits for today's DeCA queue, then DeCA Electronics seeds 2021/2022 (GMF, NeuMF x Normal, DeCA, DeCA(p)).
while pgrep -f "partB_today/run.sh" > /dev/null; do sleep 300; done
source ~/miniconda3/etc/profile.d/conda.sh; conda activate deca; cd ~/repos/DeCA; O=~/partB_today
for s in 2021 2022; do for model in GMF NeuMF-end; do for m in Normal DeCA DeCAp; do a=""; [ $m != Normal ] && a="--method $m"
  echo "$(date '+%T') DeCA electronics $model $m seed $s"
  python -u main.py --model $model --dataset electronics $a --default --seed $s > $O/deca_electronics_${model}_${m}_s$s.log 2>&1
  echo "   $(grep -A1 'CLEAN TEST' $O/deca_electronics_${model}_${m}_s$s.log | tail -1)"
done; done; done
echo "$(date '+%T') ALL DONE"
