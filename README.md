# RQ1 kit

Shared code for RQ1 of the denoising survey: one data format, one noise generator, one evaluator,
plain backbones, a resumable single-GPU job queue and a result collector. The runbook doc explains the order.

```
rq1kit/data.py       shared data format (train / valid_clean / valid_noisy / test / meta.json)
rq1kit/noise.py      clean base, N1 random, N2 popularity, N3 hard, N4 false-negative noise
rq1kit/backbone.py   MF and LightGCN with BPR or BCE loss; selects on validation; exports top-K
rq1kit/export.py     export_topk(): every method adapter calls this to write top-K files
rq1kit/evaluate.py   Recall/NDCG@10/20/50, leakage check, user and item group metrics
rq1kit/queue.py      resumable job queue for one GPU (jobs.csv -> logs/state.jsonl)
rq1kit/collect.py    all results -> tables/all_runs.csv, summary.csv (gain vs plain), partB_scorecard.csv
scripts/prepare_data.py  the 5 datasets (+ a LightGCN sanity split) into the shared format
scripts/make_jobs.py     job lists: noise, tune-plain, final-plain
scripts/pick_best.py     best tuning trial per dataset, backbone and loss
configs/methods.csv      the 13 core methods: family, year, native loss, repository
partA/papers_coding.csv  70 papers, pre-filled; fill noise_targeted, detection_signal, foundation
partA/plot_partA.py      Figure 1a and 1b for Part A
```

Quick start (after cloning the repositories into ~/repos, see the runbook Step 1):

```bash
conda activate rq1 && cd ~/rq1-kit
python scripts/prepare_data.py --dataset yelp --src ~/repos/DenoisingRec/data/yelp --out data/yelp   # repeat per dataset
python scripts/make_jobs.py noise > configs/jobs_noise.csv && python -m rq1kit.queue --jobs configs/jobs_noise.csv --logs logs/noise
python scripts/make_jobs.py tune-plain > configs/jobs_tune_plain.csv && python -m rq1kit.queue --jobs configs/jobs_tune_plain.csv --slots 2 --logs logs/tune_plain
python scripts/pick_best.py
python scripts/make_jobs.py final-plain > configs/jobs_plain.csv && python -m rq1kit.queue --jobs configs/jobs_plain.csv --slots 2 --logs logs/plain
python -m rq1kit.collect
```

Tested on CPU on MovieLens-1M end to end; data preparation and noise files tested on all five datasets.
Not yet run on a GPU or with the method adapters (Step 6 of the runbook).
Requirements: python 3.10, torch, numpy, scipy, pandas, matplotlib.
