# pc2 status

```
pc2 (anurag@home)  2026-11-12 12:42:33 IST  up since 2026-11-05 14:24:20
code c4405021 05 Nov 21:02  linger yes  disk free 949G  ram used 9/62 GB swap 0 GB 
gpu 0 %, 20578 MiB, 24564 MiB, 41
---- services ----
  survey-queue.service         active running
  survey-snapshot.service      activating start
  last snapshot: 2026-11-12 12:11:36 push ok (5628a56a; pc2 pc3)
---- gpu jobs ----
  6-10:28:54  python -m rq1kit.rq4 --signal R4 --treat drop --rate 0.1 --data data/ml1m --lr 0.001 --reg 1e-05 --epochs 100 --seed 0 
  6-10:28:45  python -m rq1kit.rq4 --signal L4 --treat graph_drop --rate 0.1 --data data/ml1m --lr 0.001 --reg 1e-05 --epochs 100 --s
  6-10:28:42  python -m rq1kit.rq4 --signal L4 --treat graph_drop --rate 0.2 --data data/ml1m --lr 0.001 --reg 1e-05 --epochs 100 --s
---- RQ4 (signal x treatment) ----
  tune ml1m: 259/273 done, 12 failed so far, median 14 min/job, ~1 h left at 4 in parallel
    failed rq4tune_ml1m_R4_resample_t1 (exit 1): torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.29 GiB. GPU 0 has a total capacity of 23.52 Gi
    failed rq4tune_ml1m_R4_resample_t2 (exit 1): torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.29 GiB. GPU 0 has a total capacity of 23.52 Gi
    failed rq4tune_ml1m_R1_graph_drop_t0 (exit 1): torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 196.00 MiB. GPU 0 has a total capacity of 23.52 
ALERT: tune: no job has finished for 148.7 h (limit 3.0 h); a job may be stuck
  final: not started
---- queue log (~/survey_queue.log) ----
  2026-11-06 02:13:30 [pc2-queue] start, code c6d3c86
  2026-11-06 02:13:31 RQ4 start: datasets [ml1m], tune 1, final seeds [all], picks from this PC
  2026-11-06 02:13:31 1 clean base and MF-BPR on it
  2026-11-06 02:13:31 2 noise files
  2026-11-06 02:13:31 3 LLM item profiles for R4
  2026-11-06 02:13:31 4 reference models and Llama scores (ML-1M)
  2026-11-06 02:13:37 4b reference models for the clean bases (teacher M1c) and the Yelp files (R2, M1, hard positives)
  2026-11-06 02:13:38 5 tuning [ml1m]
  273 of 522 jobs kept (datasets ml1m)
  68 jobs to run, 205 already done
---- recent service log lines ----
2026-11-12T11:09:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-12T11:09:36+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-12T11:40:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-12T11:40:36+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-12T12:11:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-12T12:11:36+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-12T12:42:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
