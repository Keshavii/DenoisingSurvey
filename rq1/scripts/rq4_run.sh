#!/bin/bash
# RQ4 end to end, unattended and resumable (every step skips what is already done). Normally started by
# scripts/ops/pc2_queue.sh or pc3_queue.sh (systemd service survey-queue); by hand:
#   bash ~/survey/rq1/scripts/rq4_run.sh                                  # both datasets, as on PC 2 until 5 Nov
#   DATASETS=ml1m bash ~/survey/rq1/scripts/rq4_run.sh                    # ML-1M only: tune, pick, all finals
#   DATASETS=yelp FINAL_SEEDS=1 bash ...                                  # Yelp: tune, pick, finals of seed 1
#   DATASETS=yelp TUNE=0 PICKS_FROM=picks_yelp.json FINAL_SEEDS=2 bash ...   # Yelp finals of seed 2 from picks made elsewhere
#   STOP_AFTER_PICKS=1 ...                                                 # tune and pick only (finals in a later call)
# Steps: 1 clean base and MF on it (for N3); 2 noise files N1, N3; 3 LLM item profiles (R4, ML-1M); 4 reference
# LightGCN-BCE + Llama scores per ML-1M training file (R5); 4b reference models for the clean bases and Yelp;
# 5 tuning (522 trials in all); 6 picks; 7 finals (1,169 runs in all).
# Every queue pass is followed by a second pass that reruns the failed jobs one at a time (alone on the GPU), so a job
# that ran out of GPU memory next to three others still gets its result.
# Progress: bash scripts/ops/status.sh ; per-job logs in logs/rq4_tune and logs/rq4_final.
set -eu
KIT=${KIT:-$HOME/survey/rq1}
RAW=${RAW:-$HOME/rq1-data/ml-1m}            # raw MovieLens files (titles) for the LLM prompts
LLARD=${LLARD:-$HOME/rq1-data/ml1m/llard}   # LLM item profiles built for LLaRD (embeddings reused by R4)
SLOTS=${SLOTS:-4}
DATASETS=${DATASETS:-ml1m yelp}
TUNE=${TUNE:-1}
PICKS_FROM=${PICKS_FROM:-}
FINAL_SEEDS=${FINAL_SEEDS:-}
cd "$KIT"
if [ "${NO_CONDA:-0}" != 1 ]; then
  set +u; source ~/miniconda3/etc/profile.d/conda.sh; conda activate rq1; set -u
fi
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-8} MKL_NUM_THREADS=${MKL_NUM_THREADS:-8}
# vLLM 0.32 JIT-builds a FlashInfer sampler (needs nvcc, absent on PC2); same setting as run_llard_ml1m.sh
export VLLM_USE_FLASHINFER_SAMPLER=0
say() { echo "$(date '+%F %T') $*"; }
best() { python -c "import json;b=json.load(open('configs/best_plain.json'))['$1'];print(b['lr'],b['reg'])"; }
has() { case " $DATASETS " in *" $1 "*) return 0 ;; *) return 1 ;; esac; }
DSCSV=$(echo $DATASETS | tr ' ' ',')
TAG=$(echo $DATASETS | tr ' ' '_')${FINAL_SEEDS:+_s$(echo $FINAL_SEEDS | tr ' ,' '__')}
SEEDARG=${FINAL_SEEDS:+--seeds $(echo $FINAL_SEEDS | tr ' ' ',')}
queue() {  # queue <jobs.csv> <logdir>: a normal pass, then the failed jobs again, one at a time
  python -m rq1kit.queue --jobs "$1" --slots "$SLOTS" --logs "$2"
  say "  retry pass: failed jobs of $1, one at a time"
  python -m rq1kit.queue --jobs "$1" --slots 1 --logs "$2"
}
say "RQ4 start: datasets [$DATASETS], tune $TUNE, final seeds [${FINAL_SEEDS:-all}], picks from ${PICKS_FROM:-this PC}"
for DS in $DATASETS; do [ -f data/$DS/train.tsv ] || { say "ERROR: data/$DS/train.tsv missing"; exit 2; }; done

say "1 clean base and MF-BPR on it"
for DS in $DATASETS; do
  [ -f data/$DS/train_clean.tsv ] || python -m rq1kit.noise --data data/$DS --cond clean
  read LR REG < <(best "$DS|mf|bpr")
  MF=runs/rq4_prep/${DS}_mf_clean
  [ -f $MF/topk_valid.npy ] || python -m rq1kit.backbone --data data/$DS --train_file train_clean.tsv --model mf \
      --loss bpr --lr $LR --reg $REG --seed 1 --run_dir $MF > /dev/null
done

say "2 noise files"
if has ml1m; then
  for s in 1 2 3; do
    [ -f data/ml1m/train_N1_20_s$s.tsv ] || python -m rq1kit.noise --data data/ml1m --cond N1 --rate 0.2 --seed $s
    [ -f data/ml1m/train_N3_20_s$s.tsv ] || python -m rq1kit.noise --data data/ml1m --cond N3 --rate 0.2 --seed $s \
        --mf_topk runs/rq4_prep/ml1m_mf_clean/topk_valid.npy
  done
fi
if has yelp; then
  for s in 1 2; do
    [ -f data/yelp/train_N3_20_s$s.tsv ] || python -m rq1kit.noise --data data/yelp --cond N3 --rate 0.2 --seed $s \
        --mf_topk runs/rq4_prep/yelp_mf_clean/topk_valid.npy
  done
fi

if has ml1m; then
  say "3 LLM item profiles for R4"
  if [ ! -d data/ml1m/llard ]; then cp -r "$LLARD" data/ml1m/llard; fi
  ls data/ml1m/llard/*/prf_k/itm_emb_np.pkl > /dev/null

  say "4 reference models and Llama scores (ML-1M)"
  read LR REG < <(best "ml1m|lightgcn|bce")
  for TF in train.tsv train_N1_20_s1.tsv train_N1_20_s2.tsv train_N1_20_s3.tsv train_N3_20_s1.tsv train_N3_20_s2.tsv train_N3_20_s3.tsv; do
    B=$(basename $TF .tsv); B=${B#train_}; [ "$B" = train ] && B=N0
    REF=$(python -m rq1kit.rq4 --make_ref --data data/ml1m --train_file $TF --lr $LR --reg $REG --run_dir runs/rq4_prep/unused | tail -1)
    [ -f data/ml1m/rq4_llm/$B.npz ] && continue
    say "  scoring $TF with reference $REF"
    set +u; conda activate vllm; set -u
    python -m rq1kit.rq4_llm --data data/ml1m --train_file $TF --ref $REF --raw "$RAW" --hist 20 \
      || say "  R5 scoring FAILED for $TF (its R5 cells will fail; everything else continues)"
    set +u; conda activate rq1; set -u
  done
fi

say "4b reference models for the clean bases (teacher M1c) and the Yelp files (R2, M1, hard positives)"
if has ml1m; then
  read LR REG < <(best "ml1m|lightgcn|bce")
  python -m rq1kit.rq4 --make_ref --data data/ml1m --train_file train_clean.tsv --lr $LR --reg $REG --run_dir runs/rq4_prep/unused > /dev/null
fi
if has yelp; then
  read LR REG < <(best "yelp|lightgcn|bce")
  for TF in train.tsv train_N3_20_s1.tsv train_N3_20_s2.tsv train_clean.tsv; do
    python -m rq1kit.rq4 --make_ref --data data/yelp --train_file $TF --lr $LR --reg $REG --run_dir runs/rq4_prep/unused > /dev/null
  done
fi

mkdir -p configs/rq4
if [ "$TUNE" = 1 ]; then
  say "5 tuning [$DATASETS]"
  python scripts/rq4_jobs.py tune > configs/rq4/jobs_tune.csv
  python scripts/ops/rq4_select.py filter configs/rq4/jobs_tune.csv --datasets "$DSCSV" > configs/rq4/jobs_tune_here.csv
  queue configs/rq4/jobs_tune_here.csv logs/rq4_tune

  say "6 picks"
  python scripts/rq4_jobs.py pick
  for DS in $DATASETS; do
    python scripts/ops/rq4_select.py split configs/rq4/best.json $DS configs/rq4/picks_$DS.json
  done
else
  say "6 picks from $PICKS_FROM"
  for DS in $DATASETS; do
    python scripts/ops/rq4_select.py check "$PICKS_FROM" $DS || say "  WARNING: some $DS cells have no pick (their finals are skipped)"
    python scripts/ops/rq4_select.py merge configs/rq4/best.json "$PICKS_FROM" $DS
  done
fi

if [ "${STOP_AFTER_PICKS:-0}" = 1 ]; then say "stopping after the picks (STOP_AFTER_PICKS=1); finals come in a later call"; exit 0; fi

say "7 finals [$DATASETS] seeds [${FINAL_SEEDS:-all}]"
python scripts/rq4_jobs.py final > configs/rq4/jobs_final.csv
python scripts/ops/rq4_select.py filter configs/rq4/jobs_final.csv --datasets "$DSCSV" $SEEDARG > configs/rq4/jobs_final_$TAG.csv
queue configs/rq4/jobs_final_$TAG.csv logs/rq4_final
touch configs/rq4/done_$TAG
say "RQ4 done [$DATASETS] seeds [${FINAL_SEEDS:-all}]"
