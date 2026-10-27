#!/bin/bash
# DeCA Modcloth GMF via the command line only (original, unmodified code): embedding 32 (must equal --default) then 64.
source ~/miniconda3/etc/profile.d/conda.sh; conda activate deca
cd ~/repos/DeCA; O=~/partB_extra
for d in 32 64; do
  mkdir -p output_dim$d
  C="--model GMF --dataset modcloth --epochs 40 --lambda0 0.1 --eval_freq 500 --factor_num $d --folder ./output_dim$d"
  echo "$(date '+%T') dim $d Normal"; python -u main.py $C --early_stop 1 > $O/deca_cli_dim${d}_Normal.log 2>&1
  echo "$(date '+%T') dim $d DeCA";   python -u main.py $C --early_stop 0 --method DeCA  --C_1 100 --C_2 10 --alpha 0 > $O/deca_cli_dim${d}_DeCA.log 2>&1
  echo "$(date '+%T') dim $d DeCAp";  python -u main.py $C --early_stop 0 --method DeCAp --C_1 100 --C_2 10 --alpha 1 > $O/deca_cli_dim${d}_DeCAp.log 2>&1
done
echo "$(date '+%T') ALL DONE"
