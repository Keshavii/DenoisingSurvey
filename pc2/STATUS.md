# pc2 status

```
pc2 (anurag@home)  2026-11-19 18:26:27 IST  up since 2026-11-17 18:44:08
code 6a15530f 16 Nov 20:44  linger yes  disk free 917G  ram used 8/62 GB swap 0 GB 
gpu 62 %, 7783 MiB, 24564 MiB, 47
---- services ----
  survey-kick.service          inactive dead
  survey-queue.service         active running
  survey-snapshot.service      activating start
  last snapshot: 2026-11-19 17:55:44 push ok (997791f0; pc2)
ALERT: could not fetch another PC's status over SSH (see ~/survey_snapshot.log)
---- gpu jobs ----
  02:24       timeout 12h python run_hsd_survey.py --dataset Beauty_N0_s2 --sub_model SASRec
  02:24       python run_hsd_survey.py --dataset Beauty_N0_s2 --sub_model SASRec
---- RQ4 (signal x treatment) ----
  tune ml1m: 273/273 done, 0 failed so far
  picks: picks_ml1m.json (91 cells)
  final ml1m: 831/831 done, 0 failed so far
  finished: ml1m
---- RQ10 (specialists) ----
  .done markers: 1  (s2_fmlp_beauty_n0_s2 )
  last lines of ~/rq10_seeds.log:
    2026-11-19 18:20:12 [rq10-stage2] s2_fmlp_beauty_n0_s2: start
    2026-11-19 18:24:03 [rq10-stage2] s2_fmlp_beauty_n0_s2: exit 0  3 min  peak 2557 MiB
    2026-11-19 18:24:03 [rq10-stage2] s2_hsd_beauty_n0_s2: start
  run_summary.tsv (name, exit code, minutes, peak MiB):
    s2_fmlp_beauty_n0_s2	0	3	2557
---- queue log (~/survey_queue.log) ----
  kept the logs of 0 failed jobs in logs/rq4_tune/failed
  2026-11-19 18:20:06   retry pass: failed jobs of configs/rq4/jobs_tune_here.csv, one at a time
  0 jobs to run, 273 already done
  2026-11-19 18:20:06 6 picks
  91 cells picked -> /home/anurag/survey/rq1/configs/rq4/best.json; incomplete: yelp|L1|drop (0/3), yelp|L1|reweight (0/3), yelp|L1|relabel (0/3), yelp|L1|resampl
  91 ml1m picks -> configs/rq4/picks_ml1m.json
  2026-11-19 18:20:06 7 finals [ml1m] seeds [all]
  831 of 837 jobs kept (datasets ml1m)
  0 jobs to run, 831 already done
  kept the logs of 0 failed jobs in logs/rq4_final/failed
  2026-11-19 18:20:06   retry pass: failed jobs of configs/rq4/jobs_final_ml1m.csv, one at a time
  0 jobs to run, 831 already done
  2026-11-19 18:20:06 RQ4 done [ml1m] seeds [all]
  2026-11-19 18:20:06 [pc2-queue] RQ4 ML-1M finished
  2026-11-19 18:20:06 [pc2-queue] RQ10 noise seed 2 (log ~/rq10_seeds.log, peer aura1@10.100.97.71)
---- recent service log lines ----
2026-11-19T18:09:32+05:30 home systemd[1983]: survey-queue.service: Scheduled restart job, restart counter is at 9.
2026-11-19T18:09:32+05:30 home systemd[1983]: Started survey-queue.service - Survey unattended queue (pc2).
2026-11-19T18:09:59+05:30 home systemd[1983]: survey-queue.service: Main process exited, code=exited, status=1/FAILURE
2026-11-19T18:09:59+05:30 home systemd[1983]: survey-queue.service: Failed with result 'exit-code'.
2026-11-19T18:09:59+05:30 home systemd[1983]: survey-queue.service: Consumed 16.668s CPU time.
2026-11-19T18:19:59+05:30 home systemd[1983]: survey-queue.service: Scheduled restart job, restart counter is at 10.
2026-11-19T18:19:59+05:30 home systemd[1983]: Started survey-queue.service - Survey unattended queue (pc2).
2026-11-19T18:26:26+05:30 home systemd[1983]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
