# pc2 status

```
pc2 (anurag@home)  2026-11-18 16:23:42 IST  up since 2026-11-17 18:44:08
code 6a15530f 16 Nov 20:44  linger yes  disk free 936G  ram used 3/62 GB swap 0 GB 
gpu 20 %, 765 MiB, 24564 MiB, 39
---- services ----
  survey-kick.service          inactive dead
  survey-queue.service         active running
  survey-snapshot.service      inactive dead
  last snapshot: 2026-11-18 16:05:37 push ok (7db998e6; pc2 pc3)
---- gpu jobs ----
---- RQ4 (signal x treatment) ----
  tune ml1m: 273/273 done, 0 failed so far
  picks: picks_ml1m.json (91 cells)
  final ml1m: 831/831 done, 0 failed so far
  finished: ml1m
---- queue log (~/survey_queue.log) ----
  kept the logs of 0 failed jobs in logs/rq4_tune/failed
  2026-11-18 16:23:38   retry pass: failed jobs of configs/rq4/jobs_tune_here.csv, one at a time
  0 jobs to run, 273 already done
  2026-11-18 16:23:38 6 picks
  91 cells picked -> /home/anurag/survey/rq1/configs/rq4/best.json; incomplete: yelp|L1|drop (0/3), yelp|L1|reweight (0/3), yelp|L1|relabel (0/3), yelp|L1|resampl
  91 ml1m picks -> configs/rq4/picks_ml1m.json
  2026-11-18 16:23:38 7 finals [ml1m] seeds [all]
  831 of 837 jobs kept (datasets ml1m)
  0 jobs to run, 831 already done
  kept the logs of 0 failed jobs in logs/rq4_final/failed
  2026-11-18 16:23:38   retry pass: failed jobs of configs/rq4/jobs_final_ml1m.csv, one at a time
  0 jobs to run, 831 already done
  2026-11-18 16:23:38 RQ4 done [ml1m] seeds [all]
  2026-11-18 16:23:38 [pc2-queue] RQ4 ML-1M finished
  2026-11-18 16:23:38 [pc2-queue] RQ10 noise seed 2 (log ~/rq10_seeds.log, peer aura1@10.100.97.71)
---- recent service log lines ----
2026-11-18T15:34:26+05:30 home systemd[1983]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-18T15:34:31+05:30 home systemd[1983]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-18T16:05:26+05:30 home systemd[1983]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-18T16:05:37+05:30 home systemd[1983]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-18T16:23:31+05:30 home systemd[1983]: Started survey-kick.timer - Start survey-queue if idle, every 2 h.
2026-11-18T16:23:31+05:30 home systemd[1983]: Starting survey-kick.service - Start survey-queue if it is not running...
2026-11-18T16:23:31+05:30 home systemd[1983]: Started survey-queue.service - Survey unattended queue (pc2).
2026-11-18T16:23:31+05:30 home systemd[1983]: Finished survey-kick.service - Start survey-queue if it is not running.
```
