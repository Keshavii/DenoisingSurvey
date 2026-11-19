# pc2 status

```
pc2 (anurag@home)  2026-11-19 15:51:27 IST  up since 2026-11-17 18:44:08
code 6a15530f 16 Nov 20:44  linger yes  disk free 918G  ram used 3/62 GB swap 0 GB 
gpu 0 %, 409 MiB, 24564 MiB, 42
---- services ----
  survey-kick.service          inactive dead
  survey-queue.service         failed failed
  survey-snapshot.service      activating start
ALERT: survey-queue has failed: journalctl --user -u survey-queue -n 30
  last snapshot: 2026-11-19 15:20:44 push ok (e372ffb3; pc2)
ALERT: could not fetch another PC's status over SSH (see ~/survey_snapshot.log)
---- gpu jobs ----
---- RQ4 (signal x treatment) ----
  tune ml1m: 273/273 done, 0 failed so far
  picks: picks_ml1m.json (91 cells)
  final ml1m: 831/831 done, 0 failed so far
  finished: ml1m
---- queue log (~/survey_queue.log) ----
  2026-11-18 22:53:16   retry pass: failed jobs of configs/rq4/jobs_tune_here.csv, one at a time
  0 jobs to run, 273 already done
  2026-11-18 22:53:17 6 picks
  91 cells picked -> /home/anurag/survey/rq1/configs/rq4/best.json; incomplete: yelp|L1|drop (0/3), yelp|L1|reweight (0/3), yelp|L1|relabel (0/3), yelp|L1|resampl
  91 ml1m picks -> configs/rq4/picks_ml1m.json
  2026-11-18 22:53:17 7 finals [ml1m] seeds [all]
  831 of 837 jobs kept (datasets ml1m)
  0 jobs to run, 831 already done
  kept the logs of 0 failed jobs in logs/rq4_final/failed
  2026-11-18 22:53:17   retry pass: failed jobs of configs/rq4/jobs_final_ml1m.csv, one at a time
  0 jobs to run, 831 already done
  2026-11-18 22:53:17 RQ4 done [ml1m] seeds [all]
  2026-11-18 22:53:17 [pc2-queue] RQ4 ML-1M finished
  2026-11-18 22:53:17 [pc2-queue] RQ10 noise seed 2 (log ~/rq10_seeds.log, peer aura1@10.100.97.71)
  2026-11-18 22:53:37 [pc2-queue] RQ10 seed 2 stopped with an error (last lines of ~/rq10_seeds.log: scp: Connection closed 2026-11-18 22:53:37 [rq10-seed2] Spor
---- recent service log lines ----
2026-11-19T14:34:26+05:30 home systemd[1983]: survey-queue.service: Failed with result 'exit-code'.
2026-11-19T14:34:26+05:30 home systemd[1983]: Failed to start survey-queue.service - Survey unattended queue (pc2).
2026-11-19T14:34:26+05:30 home systemd[1983]: Finished survey-kick.service - Start survey-queue if it is not running.
2026-11-19T14:49:26+05:30 home systemd[1983]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-19T14:49:44+05:30 home systemd[1983]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-19T15:20:26+05:30 home systemd[1983]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-19T15:20:44+05:30 home systemd[1983]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-19T15:51:26+05:30 home systemd[1983]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
