# pc2 status

```
pc2 (anurag@home)  2026-11-17 03:44:39 IST  up since 2026-11-05 14:24:20
code 31cd54b4 13 Nov 13:24  linger yes  disk free 936G  ram used 3/62 GB swap 0 GB 
gpu 0 %, 285 MiB, 24564 MiB, 38
---- services ----
  survey-queue.service         inactive dead
  survey-snapshot.service      activating start
  last snapshot: 2026-11-17 03:13:38 push ok (a861a3c3; pc2 pc3)
---- gpu jobs ----
---- RQ4 (signal x treatment) ----
  tune ml1m: 273/273 done, 0 failed so far
  picks: picks_ml1m.json (91 cells)
  final ml1m: 831/831 done, 0 failed so far
  finished: ml1m
---- queue log (~/survey_queue.log) ----
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
  kept the logs of 27 failed jobs in logs/rq4_final/failed
  2026-11-16 19:28:14   retry pass: failed jobs of configs/rq4/jobs_final_ml1m.csv, one at a time
  27 jobs to run, 804 already done
  2026-11-16 22:29:54 RQ4 done [ml1m] seeds [all]
  2026-11-16 22:29:54 [pc2-queue] PC2 queue complete: RQ4 ML-1M finished
---- recent service log lines ----
2026-11-17T02:11:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-17T02:11:43+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-17T02:42:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-17T02:42:37+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-17T03:13:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-17T03:13:38+05:30 home systemd[2034]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-17T03:44:32+05:30 home systemd[2034]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
