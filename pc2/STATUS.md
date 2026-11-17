# pc2 status

```
pc2 (anurag@home)  2026-11-17 23:33:27 IST  up since 2026-11-17 18:44:08
code 31cd54b4 13 Nov 13:24  linger yes  disk free 936G  ram used 2/62 GB swap 0 GB 
gpu 0 %, 176 MiB, 24564 MiB, 37
---- services ----
  survey-queue.service         inactive dead
  survey-snapshot.service      activating start
  last snapshot: 2026-11-17 23:02:32 push ok (2a848062; pc2 pc3)
---- gpu jobs ----
---- RQ4 (signal x treatment) ----
  tune ml1m: 273/273 done, 0 failed so far
  picks: picks_ml1m.json (91 cells)
  final ml1m: 831/831 done, 0 failed so far
  finished: ml1m
---- queue log (~/survey_queue.log) ----
  0 jobs to run, 273 already done
  kept the logs of 0 failed jobs in logs/rq4_tune/failed
  2026-11-17 18:44:32   retry pass: failed jobs of configs/rq4/jobs_tune_here.csv, one at a time
  0 jobs to run, 273 already done
  2026-11-17 18:44:32 6 picks
  91 cells picked -> /home/anurag/survey/rq1/configs/rq4/best.json; incomplete: yelp|L1|drop (0/3), yelp|L1|reweight (0/3), yelp|L1|relabel (0/3), yelp|L1|resampl
  91 ml1m picks -> configs/rq4/picks_ml1m.json
  2026-11-17 18:44:32 7 finals [ml1m] seeds [all]
  831 of 837 jobs kept (datasets ml1m)
  0 jobs to run, 831 already done
  kept the logs of 0 failed jobs in logs/rq4_final/failed
  2026-11-17 18:44:32   retry pass: failed jobs of configs/rq4/jobs_final_ml1m.csv, one at a time
  0 jobs to run, 831 already done
  2026-11-17 18:44:32 RQ4 done [ml1m] seeds [all]
  2026-11-17 18:44:32 [pc2-queue] PC2 queue complete: RQ4 ML-1M finished
---- recent service log lines ----
2026-11-17T22:00:26+05:30 home systemd[1983]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-17T22:00:31+05:30 home systemd[1983]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-17T22:31:26+05:30 home systemd[1983]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-17T22:31:34+05:30 home systemd[1983]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-17T23:02:26+05:30 home systemd[1983]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-17T23:02:32+05:30 home systemd[1983]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-17T23:33:26+05:30 home systemd[1983]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
