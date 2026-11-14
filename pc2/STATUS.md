# pc2 status

```
pc2 (anurag@home)  2026-11-14 19:58:33 IST  up since 2026-11-05 14:24:20
code 31cd54b4 13 Nov 13:24  linger yes  disk free 946G  ram used 10/62 GB swap 0 GB 
gpu 100 %, 5747 MiB, 24564 MiB, 64
---- services ----
  survey-queue.service         active running
  survey-snapshot.service      activating start
  last snapshot: 2026-11-14 19:27:37 push ok (d2b87074; pc2 pc3)
---- gpu jobs ----
  24:34       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal L1 --treat drop --rate 0.05 --data data/ml1m --train_fi
  24:34       bash -c python -m rq1kit.rq4 --signal L1 --treat drop --rate 0.05 --data data/ml1m --train_file train.tsv --lr 0.001 --
  24:34       python -m rq1kit.rq4 --signal L1 --treat drop --rate 0.05 --data data/ml1m --train_file train.tsv --lr 0.001 --reg 1e-0
  12:32       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal L1 --treat resample --temp 0.2 --data data/ml1m --train
  12:32       bash -c python -m rq1kit.rq4 --signal L1 --treat resample --temp 0.2 --data data/ml1m --train_file train.tsv --lr 0.001
  12:32       python -m rq1kit.rq4 --signal L1 --treat resample --temp 0.2 --data data/ml1m --train_file train.tsv --lr 0.001 --reg 1
  03:56       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal M1 --treat drop --rate 0.05 --data data/ml1m --train_fi
  03:56       bash -c python -m rq1kit.rq4 --signal M1 --treat drop --rate 0.05 --data data/ml1m --train_file train.tsv --lr 0.001 --
  03:56       python -m rq1kit.rq4 --signal M1 --treat drop --rate 0.05 --data data/ml1m --train_file train.tsv --lr 0.001 --reg 1e-0
  02:29       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal M1 --treat reweight --beta 0.25 --data data/ml1m --trai
  02:29       bash -c python -m rq1kit.rq4 --signal M1 --treat reweight --beta 0.25 --data data/ml1m --train_file train.tsv --lr 0.00
  02:29       python -m rq1kit.rq4 --signal M1 --treat reweight --beta 0.25 --data data/ml1m --train_file train.tsv --lr 0.001 --reg 
---- RQ4 (signal x treatment) ----
  tune ml1m: 273/273 done, 0 failed so far
  picks: picks_ml1m.json (91 cells)
  final ml1m: 271/831 done, 9 failed so far, median 21 min/job, ~49 h left at 4 in parallel
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
2026-11-14T18:25:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-14T18:25:37+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-14T18:25:37+05:30 home systemd[2034]: survey-snapshot.service: Consumed 4.182s CPU time.
2026-11-14T18:56:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-14T18:56:37+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-14T19:27:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-14T19:27:37+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-14T19:58:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
