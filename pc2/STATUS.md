# pc2 status

```
pc2 (anurag@home)  2026-11-06 02:13:34 IST  up since 2026-11-05 14:24:19
code c6d3c86 05 Nov 20:42  linger yes  disk free 950G  ram used 4/62 GB swap 0 GB 
gpu 15 %, 819 MiB, 24564 MiB, 52
---- services ----
  survey-queue.service         active running
  survey-snapshot.service      inactive dead
  last snapshot: 2026-11-06 02:13:31 push ok (866f09a)
---- gpu jobs ----
  00:00       python -m rq1kit.rq4 --make_ref --data data/ml1m --train_file train_N3_20_s1.tsv --lr 0.001 --reg 1e-05 --run_dir runs/
---- RQ4 (signal x treatment) ----
  tune ml1m: 205/273 done, 11 failed so far, median 14 min/job, ~4 h left at 4 in parallel
    failed rq4tune_ml1m_R4_resample_t0 (exit 1): torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.29 GiB. GPU 0 has a total capacity of 23.52 Gi
    failed rq4tune_ml1m_R4_resample_t1 (exit 1): torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.29 GiB. GPU 0 has a total capacity of 23.52 Gi
    failed rq4tune_ml1m_R4_resample_t2 (exit 1): torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.29 GiB. GPU 0 has a total capacity of 23.52 Gi
  tune yelp: 0/249 done, 0 failed so far
  final: not started
---- queue log (~/survey_queue.log) ----
  2026-11-06 02:13:30 [pc2-queue] start, code c6d3c86
  2026-11-06 02:13:31 RQ4 start: datasets [ml1m], tune 1, final seeds [all], picks from this PC
  2026-11-06 02:13:31 1 clean base and MF-BPR on it
  2026-11-06 02:13:31 2 noise files
  2026-11-06 02:13:31 3 LLM item profiles for R4
  2026-11-06 02:13:31 4 reference models and Llama scores (ML-1M)
---- recent service log lines ----
2026-11-06T02:13:25+05:30 home systemd[2034]: Stopping rq4run.service - /usr/bin/bash -c "bash ~/survey/rq1/scripts/rq4_run.sh > ~/rq4_run.log 2>&1"...
2026-11-06T02:13:25+05:30 home systemd[2034]: Stopped rq4run.service - /usr/bin/bash -c "bash ~/survey/rq1/scripts/rq4_run.sh > ~/rq4_run.log 2>&1".
2026-11-06T02:13:25+05:30 home systemd[2034]: rq4run.service: Consumed 2d 1h 14min 57.602s CPU time, 6.0G memory peak, 0B memory swap peak.
2026-11-06T02:13:25+05:30 home systemd[2034]: rq4run.service: Failed to open /run/user/1001/systemd/transient/rq4run.service: No such file or directory
2026-11-06T02:13:25+05:30 home systemd[2034]: rq4run.service: Failed to open /run/user/1001/systemd/transient/rq4run.service: No such file or directory
2026-11-06T02:13:30+05:30 home systemd[2034]: Started survey-queue.service - Survey unattended queue (pc2).
2026-11-06T02:13:31+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-06T02:13:31+05:30 home systemd[2034]: survey-snapshot.service: Consumed 1.395s CPU time, 76.5M memory peak, 0B memory swap peak.
```
