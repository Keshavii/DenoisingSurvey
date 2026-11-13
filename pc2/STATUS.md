# pc2 status

```
pc2 (anurag@home)  2026-11-13 20:43:33 IST  up since 2026-11-05 14:24:20
code 31cd54b4 13 Nov 13:24  linger yes  disk free 949G  ram used 10/62 GB swap 0 GB 
gpu 100 %, 6224 MiB, 24564 MiB, 63
---- services ----
  survey-queue.service         active running
  survey-snapshot.service      activating start
  last snapshot: 2026-11-13 20:12:37 push ok (6330d3ce; pc2 pc3)
---- gpu jobs ----
  19:24       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal M1 --treat resample --temp 0.2 --data data/ml1m --train
  19:24       bash -c python -m rq1kit.rq4 --signal M1 --treat resample --temp 0.2 --data data/ml1m --train_file train.tsv --lr 0.001
  19:24       python -m rq1kit.rq4 --signal M1 --treat resample --temp 0.2 --data data/ml1m --train_file train.tsv --lr 0.001 --reg 1
  19:14       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal M2 --treat drop --rate 0.05 --data data/ml1m --train_fi
  19:14       bash -c python -m rq1kit.rq4 --signal M2 --treat drop --rate 0.05 --data data/ml1m --train_file train.tsv --lr 0.001 --
  19:14       python -m rq1kit.rq4 --signal M2 --treat drop --rate 0.05 --data data/ml1m --train_file train.tsv --lr 0.001 --reg 1e-0
  17:18       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal M2 --treat reweight --beta 0.25 --data data/ml1m --trai
  17:18       bash -c python -m rq1kit.rq4 --signal M2 --treat reweight --beta 0.25 --data data/ml1m --train_file train.tsv --lr 0.00
  17:18       python -m rq1kit.rq4 --signal M2 --treat reweight --beta 0.25 --data data/ml1m --train_file train.tsv --lr 0.001 --reg 
  14:52       timeout -s ABRT -k 60 12h bash -c python -m rq1kit.rq4 --signal M2 --treat relabel --rate 0.05 --data data/ml1m --train
  14:52       bash -c python -m rq1kit.rq4 --signal M2 --treat relabel --rate 0.05 --data data/ml1m --train_file train.tsv --lr 0.001
  14:52       python -m rq1kit.rq4 --signal M2 --treat relabel --rate 0.05 --data data/ml1m --train_file train.tsv --lr 0.001 --reg 1
---- RQ4 (signal x treatment) ----
  tune ml1m: 273/273 done, 0 failed so far
  picks: picks_ml1m.json (91 cells)
  final ml1m: 8/831 done, 0 failed so far, median 21 min/job, ~71 h left at 4 in parallel
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
2026-11-13T18:57:43+05:30 home systemd[2034]: Started survey-queue.service - Survey unattended queue (pc2).
2026-11-13T19:10:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-13T19:10:36+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-13T19:41:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-13T19:41:37+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-13T20:12:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-13T20:12:37+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-13T20:43:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
