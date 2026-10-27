#!/bin/bash
# BOD's own LightGCN (SELFRec code, BOD's evaluator) on Yelp2018, trained longer: checks how strong BOD's baseline should be.
cd ~/repos/BOD_lgcn
for v in "A 2" "B 3"; do set -- $v
  sed -i "s#^num.max.epoch=.*#num.max.epoch=300#; s#^LightGCN=.*#LightGCN=-n_layer $2#" conf/LightGCN.conf
  echo "$(date '+%F %T') start run $1 (300 epochs, $2 layers)"; grep -E "epoch|n_layer" conf/LightGCN.conf
  echo LightGCN | python -u main.py > ~/partB_bod_lgcn/run$1_layers$2.log 2>&1
  echo "$(date '+%F %T') end   run $1"; tail -n 6 ~/partB_bod_lgcn/run$1_layers$2.log
done
echo "ALL DONE"
