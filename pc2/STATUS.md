# pc2 status

```
pc2 (anurag@home)  2026-11-15 21:48:33 IST  up since 2026-11-05 14:24:20
code 31cd54b4 13 Nov 13:24  linger yes  disk free 942G  ram used 10/62 GB swap 0 GB 
gpu 100 %, 6098 MiB, 24564 MiB, 64
---- services ----
  survey-queue.service         active running
  survey-snapshot.service      activating start
  last snapshot: 2026-11-15 21:17:37 push ok (e02501d6; pc2 pc3)
---- gpu jobs ----
  20:12       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal L4 --treat reweight --beta 0.25 --data data/ml1m --trai
  20:12       bash -c python -m rq1kit.rq4 --signal L4 --treat reweight --beta 0.25 --data data/ml1m --train_file train.tsv --lr 0.00
  20:12       python -m rq1kit.rq4 --signal L4 --treat reweight --beta 0.25 --data data/ml1m --train_file train.tsv --lr 0.001 --reg 
  15:16       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal L4 --treat relabel --rate 0.05 --data data/ml1m --train
  15:16       bash -c python -m rq1kit.rq4 --signal L4 --treat relabel --rate 0.05 --data data/ml1m --train_file train.tsv --lr 0.001
  15:16       python -m rq1kit.rq4 --signal L4 --treat relabel --rate 0.05 --data data/ml1m --train_file train.tsv --lr 0.001 --reg 1
  13:49       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal L4 --treat resample --temp 0.2 --data data/ml1m --train
  13:49       bash -c python -m rq1kit.rq4 --signal L4 --treat resample --temp 0.2 --data data/ml1m --train_file train.tsv --lr 0.001
  13:49       python -m rq1kit.rq4 --signal L4 --treat resample --temp 0.2 --data data/ml1m --train_file train.tsv --lr 0.001 --reg 1
  04:05       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal P1 --treat drop --rate 0.05 --data data/ml1m --train_fi
  04:05       bash -c python -m rq1kit.rq4 --signal P1 --treat drop --rate 0.05 --data data/ml1m --train_file train.tsv --lr 0.001 --
  04:05       python -m rq1kit.rq4 --signal P1 --treat drop --rate 0.05 --data data/ml1m --train_file train.tsv --lr 0.001 --reg 1e-0
---- RQ4 (signal x treatment) ----
  tune ml1m: 273/273 done, 0 failed so far
  picks: picks_ml1m.json (91 cells)
  final ml1m: 566/831 done, 18 failed so far, median 21 min/job, ~23 h left at 4 in parallel
    failed rq4_ml1m_R4_reweight_N3_20_s2 (exit 1): torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.27 GiB. GPU 0 has a total capacity of 23.52 Gi
    failed rq4_ml1m_R4_relabel_N3_20_s2 (exit 1): torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.27 GiB. GPU 0 has a total capacity of 23.52 Gi
    failed rq4_ml1m_R4_resample_N3_20_s2 (exit 1): torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.27 GiB. GPU 0 has a total capacity of 23.52 Gi
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
2026-11-15T20:15:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-15T20:15:43+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-15T20:46:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-15T20:46:37+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-15T20:46:37+05:30 home systemd[2034]: survey-snapshot.service: Consumed 1.022s CPU time.
2026-11-15T21:17:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-15T21:17:37+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-15T21:48:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
