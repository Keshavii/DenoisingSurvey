# pc2 status

```
pc2 (anurag@home)  2026-11-13 19:41:33 IST  up since 2026-11-05 14:24:20
code 31cd54b4 13 Nov 13:24  linger yes  disk free 949G  ram used 6/62 GB swap 0 GB 
gpu 77 %, 18399 MiB, 24564 MiB, 60
---- services ----
  survey-queue.service         active running
  survey-snapshot.service      activating start
  last snapshot: 2026-11-13 19:10:36 push ok (0954b3c3; pc2 pc3)
---- gpu jobs ----
  01:52       timeout -s ABRT -k 60 4h python -m rq1kit.rq4 --signal R4 --treat resample --temp 0.2 --data data/ml1m --lr 0.001 --reg
  01:52       python -m rq1kit.rq4 --signal R4 --treat resample --temp 0.2 --data data/ml1m --lr 0.001 --reg 1e-05 --epochs 100 --see
---- RQ4 (signal x treatment) ----
  tune ml1m: 272/273 done, 1 failed so far, median 14 min/job, ~0 h left at 4 in parallel
    failed rq4tune_ml1m_R4_resample_t2 (exit 1): {'epoch': 35, 'iteration': 13685, 'loss': 0.6540620934751578, 'seconds': 108.4, 'valid_clean_ndcg@20': 0.09591
  final: not started
---- queue log (~/survey_queue.log) ----
  273 of 522 jobs kept (datasets ml1m)
  14 jobs to run, 259 already done
  2026-11-13 18:51:00   retry pass: failed jobs of configs/rq4/jobs_tune_here.csv, one at a time
  2026-11-13 18:57:43 [pc2-queue] start, code 31cd54b4
  2026-11-13 18:57:43 RQ4 start: datasets [ml1m], tune 1, final seeds [all], picks from this PC
  2026-11-13 18:57:43 1 clean base and MF-BPR on it
  2026-11-13 18:57:43 2 noise files
  2026-11-13 18:57:43 3 LLM item profiles for R4
  2026-11-13 18:57:43 4 reference models and Llama scores (ML-1M)
  2026-11-13 18:57:49 4b reference models for the clean bases (teacher M1c) and the Yelp files (R2, M1, hard positives)
  2026-11-13 18:57:49 5 tuning [ml1m]
  273 of 522 jobs kept (datasets ml1m)
  10 jobs to run, 263 already done
  kept the logs of 9 failed jobs in logs/rq4_tune/failed
  2026-11-13 19:03:19   retry pass: failed jobs of configs/rq4/jobs_tune_here.csv, one at a time
---- recent service log lines ----
2026-11-13T18:40:30+05:30 home systemd[2034]: Started survey-queue.service - Survey unattended queue (pc2).
2026-11-13T18:57:42+05:30 home systemd[2034]: Stopping survey-queue.service - Survey unattended queue (pc2)...
2026-11-13T18:57:43+05:30 home systemd[2034]: Stopped survey-queue.service - Survey unattended queue (pc2).
2026-11-13T18:57:43+05:30 home systemd[2034]: survey-queue.service: Consumed 38min 32.402s CPU time.
2026-11-13T18:57:43+05:30 home systemd[2034]: Started survey-queue.service - Survey unattended queue (pc2).
2026-11-13T19:10:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-13T19:10:36+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-13T19:41:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
