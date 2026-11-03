#!/bin/bash
# RQ4 end to end on PC 2, unattended and resumable (every step skips what is already done).
#   systemd-run --user --unit=rq4 --collect bash -c "bash ~/survey/rq1/scripts/rq4_run.sh > ~/rq4.log 2>&1"
# Progress: tail ~/rq4.log ; per-job logs in logs/rq4_tune and logs/rq4_final.
# Steps: 1 clean base and MF on it (for N3); 2 noise files N1, N3; 3 LLM item profiles in place (R4);
# 4 reference LightGCN-BCE + Llama scores for each ML-1M training file (R5); 5 tuning; 6 picks; 7 finals.
set -eu
KIT=${KIT:-$HOME/survey/rq1}
RAW=${RAW:-$HOME/rq1-data/ml-1m}            # raw MovieLens files (titles) for the LLM prompts
LLARD=${LLARD:-$HOME/rq1-data/ml1m/llard}   # LLM item profiles built for LLaRD (embeddings reused by R4)
SLOTS=${SLOTS:-4}
cd "$KIT"
source ~/miniconda3/etc/profile.d/conda.sh
conda activate rq1
export OMP_NUM_THREADS=8 MKL_NUM_THREADS=8
say() { echo "$(date '+%F %T') $*"; }
best() { python -c "import json;b=json.load(open('configs/best_plain.json'))['$1'];print(b['lr'],b['reg'])"; }

say "1 clean base and MF-BPR on it"
for DS in ml1m yelp; do
  [ -f data/$DS/train_clean.tsv ] || python -m rq1kit.noise --data data/$DS --cond clean
  read LR REG < <(best "$DS|mf|bpr")
  MF=runs/rq4_prep/${DS}_mf_clean
  [ -f $MF/topk_valid.npy ] || python -m rq1kit.backbone --data data/$DS --train_file train_clean.tsv --model mf \
      --loss bpr --lr $LR --reg $REG --seed 1 --run_dir $MF > /dev/null
done

say "2 noise files"
for s in 1 2 3; do
  [ -f data/ml1m/train_N1_20_s$s.tsv ] || python -m rq1kit.noise --data data/ml1m --cond N1 --rate 0.2 --seed $s
  [ -f data/ml1m/train_N3_20_s$s.tsv ] || python -m rq1kit.noise --data data/ml1m --cond N3 --rate 0.2 --seed $s \
      --mf_topk runs/rq4_prep/ml1m_mf_clean/topk_valid.npy
done
for s in 1 2; do
  [ -f data/yelp/train_N3_20_s$s.tsv ] || python -m rq1kit.noise --data data/yelp --cond N3 --rate 0.2 --seed $s \
      --mf_topk runs/rq4_prep/yelp_mf_clean/topk_valid.npy
done

say "3 LLM item profiles for R4"
if [ ! -d data/ml1m/llard ]; then cp -r "$LLARD" data/ml1m/llard; fi
ls data/ml1m/llard/*/prf_k/itm_emb_np.pkl > /dev/null

say "4 reference models and Llama scores (ML-1M)"
read LR REG < <(best "ml1m|lightgcn|bce")
for TF in train.tsv train_N1_20_s1.tsv train_N1_20_s2.tsv train_N1_20_s3.tsv train_N3_20_s1.tsv train_N3_20_s2.tsv train_N3_20_s3.tsv; do
  B=$(basename $TF .tsv); B=${B#train_}; [ "$B" = train ] && B=N0
  [ -f data/ml1m/rq4_llm/$B.npz ] && continue
  REF=$(python -m rq1kit.rq4 --make_ref --data data/ml1m --train_file $TF --lr $LR --reg $REG --run_dir runs/rq4_prep/unused | tail -1)
  say "  scoring $TF with reference $REF"
  conda activate vllm
  python -m rq1kit.rq4_llm --data data/ml1m --train_file $TF --ref $REF --raw "$RAW" --hist 20
  conda activate rq1
done

say "5 tuning"
mkdir -p configs/rq4
python scripts/rq4_jobs.py tune > configs/rq4/jobs_tune.csv
python -m rq1kit.queue --jobs configs/rq4/jobs_tune.csv --slots $SLOTS --logs logs/rq4_tune

say "6 picks"
python scripts/rq4_jobs.py pick

say "7 finals"
python scripts/rq4_jobs.py final > configs/rq4/jobs_final.csv
python -m rq1kit.queue --jobs configs/rq4/jobs_final.csv --slots $SLOTS --logs logs/rq4_final
say "RQ4 done"
