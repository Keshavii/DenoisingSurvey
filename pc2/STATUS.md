# pc2 status

```
pc2 (anurag@home)  2026-11-06 02:13:26 IST  up since 2026-11-05 14:24:19
code c6d3c86 05 Nov 20:42  linger yes  disk free 950G  ram used 3/62 GB swap 0 GB 
gpu 0 %, 749 MiB, 24564 MiB, 56
---- services ----
  survey-snapshot.service      activating start
ALERT: survey-queue is not enabled (will not start after a reboot)
---- gpu jobs ----
---- RQ4 (signal x treatment) ----
  tune ml1m: 205/273 done, 11 failed so far, median 14 min/job, ~4 h left at 4 in parallel
    failed rq4tune_ml1m_R4_resample_t0 (exit 1): torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.29 GiB. GPU 0 has a total capacity of 23.52 Gi
    failed rq4tune_ml1m_R4_resample_t1 (exit 1): torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.29 GiB. GPU 0 has a total capacity of 23.52 Gi
    failed rq4tune_ml1m_R4_resample_t2 (exit 1): torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.29 GiB. GPU 0 has a total capacity of 23.52 Gi
  tune yelp: 0/249 done, 0 failed so far
  final: not started
---- recent service log lines ----
2026-11-06T02:13:25+05:30 home systemd[2034]: Started survey-snapshot.timer - Survey snapshot every 30 min.
2026-11-06T02:13:25+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-06T02:13:25+05:30 home systemd[2034]: Stopping rq4run.service - /usr/bin/bash -c "bash ~/survey/rq1/scripts/rq4_run.sh > ~/rq4_run.log 2>&1"...
2026-11-06T02:13:25+05:30 home systemd[2034]: Stopped rq4run.service - /usr/bin/bash -c "bash ~/survey/rq1/scripts/rq4_run.sh > ~/rq4_run.log 2>&1".
2026-11-06T02:13:25+05:30 home systemd[2034]: rq4run.service: Consumed 2d 1h 14min 57.602s CPU time, 6.0G memory peak, 0B memory swap peak.
2026-11-06T02:13:25+05:30 home systemd[2034]: rq4run.service: Failed to open /run/user/1001/systemd/transient/rq4run.service: No such file or directory
2026-11-06T02:13:25+05:30 home systemd[2034]: rq4run.service: Failed to open /run/user/1001/systemd/transient/rq4run.service: No such file or directory
```
