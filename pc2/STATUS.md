# pc2 status

```
pc2 (anurag@home)  2026-11-13 22:16:33 IST  up since 2026-11-05 14:24:20
code 31cd54b4 13 Nov 13:24  linger yes  disk free 949G  ram used 10/62 GB swap 0 GB 
gpu 100 %, 6460 MiB, 24564 MiB, 64
---- services ----
  survey-queue.service         active running
  survey-snapshot.service      activating start
  last snapshot: 2026-11-13 21:45:37 push ok (92f368dd; pc2 pc3)
---- gpu jobs ----
  27:53       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal L3 --treat drop --rate 0.1 --data data/ml1m --train_fil
  27:53       bash -c python -m rq1kit.rq4 --signal L3 --treat drop --rate 0.1 --data data/ml1m --train_file train.tsv --lr 0.001 --r
  27:53       python -m rq1kit.rq4 --signal L3 --treat drop --rate 0.1 --data data/ml1m --train_file train.tsv --lr 0.001 --reg 1e-05
  21:21       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal L3 --treat reweight --beta 0.25 --data data/ml1m --trai
  21:21       bash -c python -m rq1kit.rq4 --signal L3 --treat reweight --beta 0.25 --data data/ml1m --train_file train.tsv --lr 0.00
  21:21       python -m rq1kit.rq4 --signal L3 --treat reweight --beta 0.25 --data data/ml1m --train_file train.tsv --lr 0.001 --reg 
  06:41       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal L3 --treat relabel --rate 0.05 --data data/ml1m --train
  06:41       bash -c python -m rq1kit.rq4 --signal L3 --treat relabel --rate 0.05 --data data/ml1m --train_file train.tsv --lr 0.001
  06:41       python -m rq1kit.rq4 --signal L3 --treat relabel --rate 0.05 --data data/ml1m --train_file train.tsv --lr 0.001 --reg 1
  02:27       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal L3 --treat resample --temp 0.2 --data data/ml1m --train
  02:27       bash -c python -m rq1kit.rq4 --signal L3 --treat resample --temp 0.2 --data data/ml1m --train_file train.tsv --lr 0.001
  02:26       python -m rq1kit.rq4 --signal L3 --treat resample --temp 0.2 --data data/ml1m --train_file train.tsv --lr 0.001 --reg 1
---- RQ4 (signal x treatment) ----
  tune ml1m: 273/273 done, 0 failed so far
  picks: picks_ml1m.json (91 cells)
  final ml1m: 25/831 done, 0 failed so far, median 21 min/job, ~71 h left at 4 in parallel
---- queue log (~/survey_queue.log) ----
  2026-11-13 18:57:43 2 noise files
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
---- recent service log lines ----
2026-11-13T20:43:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-13T20:43:36+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-13T21:14:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-13T21:14:36+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-13T21:45:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-13T21:45:37+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-13T22:16:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
