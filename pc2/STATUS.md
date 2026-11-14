# pc2 status

```
pc2 (anurag@home)  2026-11-14 17:23:34 IST  up since 2026-11-05 14:24:20
code 31cd54b4 13 Nov 13:24  linger yes  disk free 946G  ram used 10/62 GB swap 0 GB 
gpu 100 %, 6011 MiB, 24564 MiB, 64
---- services ----
  survey-queue.service         active running
  survey-snapshot.service      activating start
  last snapshot: 2026-11-14 16:52:36 push ok (378b9db3; pc2 pc3)
---- gpu jobs ----
  16:03       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal L1 --treat graph_reweight --beta 0.5 --data data/ml1m -
  16:03       bash -c python -m rq1kit.rq4 --signal L1 --treat graph_reweight --beta 0.5 --data data/ml1m --train_file train_N3_20_s1
  16:03       python -m rq1kit.rq4 --signal L1 --treat graph_reweight --beta 0.5 --data data/ml1m --train_file train_N3_20_s1.tsv --l
  13:59       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal L1 --treat user_reweight --beta 0.25 --data data/ml1m -
  13:59       bash -c python -m rq1kit.rq4 --signal L1 --treat user_reweight --beta 0.25 --data data/ml1m --train_file train_N3_20_s1
  13:59       python -m rq1kit.rq4 --signal L1 --treat user_reweight --beta 0.25 --data data/ml1m --train_file train_N3_20_s1.tsv --l
  09:52       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal L1 --treat soft_relabel --lam 0.3 --data data/ml1m --tr
  09:52       bash -c python -m rq1kit.rq4 --signal L1 --treat soft_relabel --lam 0.3 --data data/ml1m --train_file train_N3_20_s1.ts
  09:52       python -m rq1kit.rq4 --signal L1 --treat soft_relabel --lam 0.3 --data data/ml1m --train_file train_N3_20_s1.tsv --lr 0
  04:29       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal M1 --treat graph_drop --rate 0.2 --data data/ml1m --tra
  04:29       bash -c python -m rq1kit.rq4 --signal M1 --treat graph_drop --rate 0.2 --data data/ml1m --train_file train_N3_20_s1.tsv
  04:29       python -m rq1kit.rq4 --signal M1 --treat graph_drop --rate 0.2 --data data/ml1m --train_file train_N3_20_s1.tsv --lr 0.
---- RQ4 (signal x treatment) ----
  tune ml1m: 273/273 done, 0 failed so far
  picks: picks_ml1m.json (91 cells)
  final ml1m: 237/831 done, 9 failed so far, median 21 min/job, ~52 h left at 4 in parallel
    failed rq4_ml1m_R4_reweight_N3_20_s1 (exit 1): torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.27 GiB. GPU 0 has a total capacity of 23.52 Gi
    failed rq4_ml1m_R4_relabel_N3_20_s1 (exit 1): torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.27 GiB. GPU 0 has a total capacity of 23.52 Gi
    failed rq4_ml1m_R4_resample_N3_20_s1 (exit 1): torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.27 GiB. GPU 0 has a total capacity of 23.52 Gi
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
2026-11-14T15:50:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-14T15:50:38+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-14T16:21:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-14T16:21:36+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-14T16:52:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-14T16:52:36+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-14T17:23:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
