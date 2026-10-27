#!/bin/bash
# DrRL Part B (AAAI 2025): settings from the paper's Table 8 (IID). DrRL: --lr --weight_decay, {lr_margin=--lr2, gamma=--renyi_omega, beta0=--renyi_margin};
# SL baseline: --loss softmax --ssm_temp tau. 1024 negatives, batch 1024, dim 64; XSimGCL: cl_rate 0.001, noise 0.2, cl layer 1, cl temp 0.2.
# Repository has no environment.yaml (named in README): env drrl (ddrm clone + nni, tensorboardX); seed 2023 (code default).
source ~/miniconda3/etc/profile.d/conda.sh; conda activate drrl; cd ~/repos/DrRL; O=~/partB_drrl
X="--eps 0.2 --cl_layer 1 --cl_rate 0.001 --cl_temp 0.2"
run() { tag=$1; shift; echo "$(date '+%F %T') start $tag"
  python -u main.py --datapath IID_Data --num_negative_items 1024 --train_batch 1024 --recdim 64 --cuda 0 "$@" > $O/$tag.log 2>&1
  echo "$(date '+%F %T') end   $tag   $(grep -A1 '\[Test\]' $O/$tag.log | tail -1 | cut -c1-200)"; }
#   tag                        dataset             model    lr     wd  lr2   gamma beta0
while read tag ds m lr wd lr2 g b0; do [ -z "$tag" ] && continue
  ex=""; [ $m = XSimGCL ] && ex="$X"
  run drrl_$tag --dataset $ds --model $m --loss DrRL --lr $lr --weight_decay $wd --lr2 $lr2 --renyi_omega $g --renyi_margin $b0 $ex
done <<'L'
beauty_mf        amazonBeauty      mf      1e-4 0 1e-5 1.15 0.90
beauty_lgn       amazonBeauty      lgn     1e-2 0 1e-4 1.17 0.90
beauty_xsim      amazonBeauty      XSimGCL 1e-2 0 1e-5 1.16 0.85
elec_mf          amazonElectronics mf      1e-1 0 1e-5 1.27 0.70
elec_lgn         amazonElectronics lgn     1e-1 0 1e-4 1.21 0.80
elec_xsim        amazonElectronics XSimGCL 1e-2 0 1e-4 1.19 0.85
kitchen_mf       amazonKitchen     mf      1e-3 0 1e-4 1.20 0.85
kitchen_lgn      amazonKitchen     lgn     1e-4 0 1e-4 1.21 0.85
kitchen_xsim     amazonKitchen     XSimGCL 1e-2 0 1e-4 1.24 0.85
gowalla_mf       Gowalla           mf      1e-5 0 1e-5 1.09 0.85
gowalla_lgn      Gowalla           lgn     1e-1 0 1e-4 1.08 0.90
gowalla_xsim     Gowalla           XSimGCL 1e-1 0 1e-4 1.09 0.90
L
#   tag            dataset            model    lr    wd  tau
while read tag ds m lr wd tau; do [ -z "$tag" ] && continue
  ex=""; [ $m = XSimGCL ] && ex="$X"
  run sl_$tag --dataset $ds --model $m --loss softmax --lr $lr --weight_decay $wd --ssm_temp $tau $ex
done <<'L'
beauty_mf        amazonBeauty      mf      1e-1 0 0.20
beauty_lgn       amazonBeauty      lgn     1e-2 0 0.21
beauty_xsim      amazonBeauty      XSimGCL 1e-1 0 0.18
elec_mf          amazonElectronics mf      1e-1 0 0.26
elec_lgn         amazonElectronics lgn     1e-2 0 0.25
elec_xsim        amazonElectronics XSimGCL 1e-2 0 0.23
kitchen_mf       amazonKitchen     mf      1e-2 0 0.20
kitchen_lgn      amazonKitchen     lgn     1e-1 0 0.25
kitchen_xsim     amazonKitchen     XSimGCL 1e-2 0 0.18
gowalla_mf       Gowalla           mf      1e-2 0 0.09
gowalla_lgn      Gowalla           lgn     1e-1 0 0.08
gowalla_xsim     Gowalla           XSimGCL 1e-1 0 0.07
L
echo "$(date '+%F %T') ALL DONE"
