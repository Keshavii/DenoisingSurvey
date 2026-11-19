# pc2 status

```
pc2 (anurag@home)  2026-11-20 00:07:27 IST  up since 2026-11-17 18:44:08
code 6a15530f 16 Nov 20:44  linger yes  disk free 912G  ram used 7/62 GB swap 0 GB 
gpu 66 %, 2933 MiB, 24564 MiB, 61
---- services ----
  survey-kick.service          inactive dead
  survey-queue.service         active running
  survey-snapshot.service      activating start
  last snapshot: 2026-11-19 23:36:31 push ok (a11ceeb8; pc2 pc3)
---- gpu jobs ----
  03:39:58    timeout 12h bash -c python main.py -tf /home/anurag/survey/rq10/data_s2/Sports_and_Outdoors_N0_s2/train.dat -vf /home/a
  03:39:58    bash -c python main.py -tf /home/anurag/survey/rq10/data_s2/Sports_and_Outdoors_N0_s2/train.dat -vf /home/anurag/survey
  20:06       python main.py -tf /home/anurag/survey/rq10/data_s2/Sports_and_Outdoors_N0_s2/train.dat -vf /home/anurag/survey/rq10/da
  00:00       python main.py -tf /home/anurag/survey/rq10/data_s2/Sports_and_Outdoors_N0_s2/train.dat -vf /home/anurag/survey/rq10/da
  00:00       python main.py -tf /home/anurag/survey/rq10/data_s2/Sports_and_Outdoors_N0_s2/train.dat -vf /home/anurag/survey/rq10/da
  00:00       python main.py -tf /home/anurag/survey/rq10/data_s2/Sports_and_Outdoors_N0_s2/train.dat -vf /home/anurag/survey/rq10/da
  00:00       python main.py -tf /home/anurag/survey/rq10/data_s2/Sports_and_Outdoors_N0_s2/train.dat -vf /home/anurag/survey/rq10/da
---- RQ4 (signal x treatment) ----
  tune ml1m: 273/273 done, 0 failed so far
  picks: picks_ml1m.json (91 cells)
  final ml1m: 831/831 done, 0 failed so far
  finished: ml1m
---- RQ10 (specialists) ----
  .done markers: 5  (s2_hsd_sports_and_outdoors_n0_s2 s2_steam_beauty_n0_s2 s2_hsd_beauty_n0_s2 s2_fmlp_beauty_n0_s2 s2_fmlp_sports_and_outdoors_n0_s2 )
  last lines of ~/rq10_seeds.log:
    2026-11-19 20:20:14 [rq10-stage2] s2_hsd_sports_and_outdoors_n0_s2: start
    2026-11-19 20:27:28 [rq10-stage2] s2_hsd_sports_and_outdoors_n0_s2: exit 0  7 min  peak 7763 MiB
    2026-11-19 20:27:28 [rq10-stage2] s2_steam_sports_and_outdoors_n0_s2: start
  run_summary.tsv (name, exit code, minutes, peak MiB):
    s2_fmlp_beauty_n0_s2	0	3	2557
    s2_hsd_beauty_n0_s2	0	7	7783
    s2_steam_beauty_n0_s2	0	101	22583
    s2_fmlp_sports_and_outdoors_n0_s2	0	6	2601
    s2_hsd_sports_and_outdoors_n0_s2	0	7	7763
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
2026-11-19T22:34:31+05:30 home systemd[1983]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-19T22:38:26+05:30 home systemd[1983]: Starting survey-kick.service - Start survey-queue if it is not running...
2026-11-19T22:38:26+05:30 home systemd[1983]: Finished survey-kick.service - Start survey-queue if it is not running.
2026-11-19T23:05:26+05:30 home systemd[1983]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-19T23:05:31+05:30 home systemd[1983]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-19T23:36:26+05:30 home systemd[1983]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-19T23:36:31+05:30 home systemd[1983]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-20T00:07:26+05:30 home systemd[1983]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
