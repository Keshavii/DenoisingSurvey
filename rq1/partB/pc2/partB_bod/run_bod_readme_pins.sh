#!/bin/bash
# BOD and LightGCN on yelp2018 with the README's versions (numpy 1.20.3, scipy 1.6.2, numba 0.53.1, torch 1.13.1+cu117 (1.10.0+cu111 fails in cuSPARSE on the RTX 4090)).
# Same official code, confs and edits as run_bod.sh. Starts when DDRM's Amazon-Book seeds are finished.
source ~/miniconda3/etc/profile.d/conda.sh; conda activate bod_r; cd ~/repos/BOD
mkdir -p ~/partB_bod/readme_pins
while systemctl --user is-active --quiet ddrm-seeds; do sleep 60; done
python -c "import numpy,scipy,numba,torch; print('versions', numpy.__version__, scipy.__version__, numba.__version__, torch.__version__)"
ds=yelp2018
for m in BOD LightGCN; do
  out=~/partB_bod/readme_pins/${m}_${ds}.log
  if grep -q "^Running time" $out 2>/dev/null; then echo "skip $m"; continue; fi
  sed -i "s#^training.set=.*#training.set=./dataset/$ds/train.txt#; s#^test.set=.*#test.set=./dataset/$ds/test.txt#" conf/$m.conf
  sed -i "s#^dataset.name=.*#dataset.name=$ds#" conf/$m.conf
  echo "$(date '+%F %T') start $m $ds"
  echo $m | python -u main.py > $out 2>&1
  echo "$(date '+%F %T') end   $m $ds   $(tail -6 $out | grep -E 'Recall|NDCG' | tr '\n' ' ')"
done
echo "ALL DONE"
