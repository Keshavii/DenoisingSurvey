# pc2 status

```
pc2 (anurag@home)  2026-11-14 03:57:33 IST  up since 2026-11-05 14:24:20
code 31cd54b4 13 Nov 13:24  linger yes  disk free 948G  ram used 10/62 GB swap 0 GB 
gpu 100 %, 5512 MiB, 24564 MiB, 64
---- services ----
  survey-queue.service         active running
  survey-snapshot.service      activating start
  last snapshot: 2026-11-14 03:26:36 push ok (d1e4d646; pc2 pc3)
---- gpu jobs ----
  16:56       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal none --treat reshape --ssl_reg 0.05 --data data/ml1m --
  16:56       bash -c python -m rq1kit.rq4 --signal none --treat reshape --ssl_reg 0.05 --data data/ml1m --train_file train.tsv --lr 
  16:56       python -m rq1kit.rq4 --signal none --treat reshape --ssl_reg 0.05 --data data/ml1m --train_file train.tsv --lr 0.001 --
  14:38       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal none --treat none --data data/ml1m --train_file train_N
  14:38       bash -c python -m rq1kit.rq4 --signal none --treat none --data data/ml1m --train_file train_N1_20_s1.tsv --lr 0.001 --r
  14:38       python -m rq1kit.rq4 --signal none --treat none --data data/ml1m --train_file train_N1_20_s1.tsv --lr 0.001 --reg 1e-05
  05:31       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal L1 --treat drop --rate 0.05 --data data/ml1m --train_fi
  05:31       bash -c python -m rq1kit.rq4 --signal L1 --treat drop --rate 0.05 --data data/ml1m --train_file train_N1_20_s1.tsv --lr
  05:31       python -m rq1kit.rq4 --signal L1 --treat drop --rate 0.05 --data data/ml1m --train_file train_N1_20_s1.tsv --lr 0.001 -
  03:14       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal L1 --treat reweight --beta 0.25 --data data/ml1m --trai
  03:14       bash -c python -m rq1kit.rq4 --signal L1 --treat reweight --beta 0.25 --data data/ml1m --train_file train_N1_20_s1.tsv 
  03:14       python -m rq1kit.rq4 --signal L1 --treat reweight --beta 0.25 --data data/ml1m --train_file train_N1_20_s1.tsv --lr 0.0
---- RQ4 (signal x treatment) ----
  tune ml1m: 273/273 done, 0 failed so far
  picks: picks_ml1m.json (91 cells)
  final ml1m: 88/831 done, 3 failed so far, median 21 min/job, ~66 h left at 4 in parallel
    failed rq4_ml1m_R4_reweight_N0_s1 (exit 1): torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.29 GiB. GPU 0 has a total capacity of 23.52 Gi
    failed rq4_ml1m_R4_relabel_N0_s1 (exit 1): torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.29 GiB. GPU 0 has a total capacity of 23.52 Gi
    failed rq4_ml1m_R4_resample_N0_s1 (exit 1): torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.29 GiB. GPU 0 has a total capacity of 23.52 Gi
---- queue log (~/survey_queue.log) ----
  2026-11-13 18:57:43 3 LLM item profiles for R4
  2026-11-13 18:57:43 4 reference models and Llama scores (ML-1M)
  2026-11-13 18:57:49 4b reference models for the clean bases (teacher M1c) and the Yelp files (R2, M1, hard positives)
  2026-11-13 18:57:49 5 tuning [ml1m]
  273 of 522 jobs kept (datasets ml1m)
  10 jobs to run, 263 already done
  kept the logs of 9 failed jobs in logs/rq4_tune/failed
  2026-11-13 19:03:19   retry pass: failed jobs of configs/rq4/jobs_tune_here.csv, one at a time
  9 jobs to run, 264 already done
  2026-11-13 19:44:56 6 picks
  91 cells picked -> /home/anurag/survey/rq1/configs/rq4/best.json; incomplete: yelp|L1|drop (0/3), yelp|L1|reweight (0/3), yelp|L1|relabel (0/3), yelp|L1|resampl
  91 ml1m picks -> configs/rq4/picks_ml1m.json
  2026-11-13 19:44:56 7 finals [ml1m] seeds [all]
  831 of 837 jobs kept (datasets ml1m)
  831 jobs to run, 0 already done
---- recent service log lines ----
2026-11-14T02:24:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-14T02:24:36+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-14T02:55:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-14T02:55:37+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-14T03:26:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-14T03:26:36+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-14T03:57:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
