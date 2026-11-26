# pc2 status

```
pc2 (anurag@home)  2026-11-26 12:38:27 IST  up since 2026-11-17 18:44:08
code 6a15530f 16 Nov 20:44  linger yes  disk free 875G  ram used 7/62 GB swap 0 GB 
gpu 97 %, 17449 MiB, 24564 MiB, 65
---- services ----
  rq10-seed3.service           active running
  survey-kick.service          inactive dead
  survey-queue.service         inactive dead
  survey-snapshot.service      activating start
  last snapshot: 2026-11-26 12:07:31 push ok (92ca4df4; pc2 pc3)
---- gpu jobs ----
  02:22:29    timeout 12h bash -c python main.py -tf /home/anurag/survey/rq10/data_s2/Sports_and_Outdoors_I10_s3/train.dat -vf /home/
  02:22:29    bash -c python main.py -tf /home/anurag/survey/rq10/data_s2/Sports_and_Outdoors_I10_s3/train.dat -vf /home/anurag/surve
  02:22:29    python main.py -tf /home/anurag/survey/rq10/data_s2/Sports_and_Outdoors_I10_s3/train.dat -vf /home/anurag/survey/rq10/d
  00:32       python main.py -tf /home/anurag/survey/rq10/data_s2/Sports_and_Outdoors_I10_s3/train.dat -vf /home/anurag/survey/rq10/d
  00:32       python main.py -tf /home/anurag/survey/rq10/data_s2/Sports_and_Outdoors_I10_s3/train.dat -vf /home/anurag/survey/rq10/d
  00:32       python main.py -tf /home/anurag/survey/rq10/data_s2/Sports_and_Outdoors_I10_s3/train.dat -vf /home/anurag/survey/rq10/d
  00:32       python main.py -tf /home/anurag/survey/rq10/data_s2/Sports_and_Outdoors_I10_s3/train.dat -vf /home/anurag/survey/rq10/d
---- RQ4 (signal x treatment) ----
  tune ml1m: 273/273 done, 0 failed so far
  picks: picks_ml1m.json (91 cells)
  final ml1m: 831/831 done, 0 failed so far
  finished: ml1m
---- RQ10 (specialists) ----
  .done markers: 41  (s2_fmlp_yelp_i20_s2 s2_hsd_sports_and_outdoors_n0_s3 s2_fmlp_beauty_i10_s3 s2_hsd_beauty_i10_s2 s2_steam_sports_and_outdoors_i10_s2 s2_steam_yelp_i10_s2 s2_hsd_yelp_i20_s2 s2_hsd_sports_and_outdoors_n0_s2 s2_fmlp_beauty_i10_s2 s2_hsd_yelp_i10_s2 s2_fmlp_sports_and_outdoors_i10_s3 s2_steam_beauty_n0_s2 s2_steam_yelp_i20_s2 s2_fmlp_sports_and_outdoors_n0_s3 s2_steam_sports_and_outdoors_i20_s2 s2_hsd_sports_and_outdoors_i10_s2 s2_steam_beauty_n0_s3 s2_steam_beauty_i20_s2 s2_steam_sports_and_outdoors_n0_s3 s2_steam_beauty_i10_s3 s2_hsd_sports_and_outdoors_i10_s3 s2_fmlp_beauty_n0_s3 s2_fmlp_yelp_i10_s2 s2_hsd_beauty_n0_s2 s2_steam_yelp_n0_s3 s2_hsd_beauty_i20_s2 s2_steam_beauty_i10_s2 s2_steam_sports_and_outdoors_n0_s2 s2_fmlp_beauty_n0_s2 s2_fmlp_yelp_n0_s2 s2_hsd_yelp_n0_s3 s2_hsd_beauty_n0_s3 s2_hsd_beauty_i10_s3 s2_fmlp_sports_and_outdoors_i10_s2 s2_fmlp_beauty_i20_s2 s2_hsd_sports_and_outdoors_i20_s2 s2_fmlp_sports_and_outdoors_n0_s2 s2_hsd_yelp_n0_s2 s2_steam_yelp_n0_s2 s2_fmlp_yelp_n0_s3 s2_fmlp_sports_and_outdoors_i20_s2 )
  last lines of ~/rq10_seeds.log:
      STEAM         Yelp                 N0   s3  Recall@10 0.0627  NDCG@10 0.0347
    2026-11-26 11:48:37 [rq10-stage2] stage 2 complete: 41 runs with results (table: /home/anurag/survey/rq10/results/stage2_summary.tsv)
    2026-11-26 11:48:37 [rq10-seed2] stage 2 seed 2 finished with exit 0
  stage 2 (full ranking, Recall@10 / NDCG@10):
    method    dataset              level                seed  recall10  ndcg10  source                            
    FMLP-Rec  Beauty               N0                   2     0.0562    0.0294  logs/run_s2_fmlp_beauty_n0_s2.log 
    FMLP-Rec  Beauty               I10                  2     0.0521    0.0270  logs/run_s2_fmlp_beauty_i10_s2.log
    FMLP-Rec  Beauty               I20                  2     0.0494    0.0253  logs/run_s2_fmlp_beauty_i20_s2.log
    FMLP-Rec  Beauty               N0                   3     0.0562    0.0294  logs/run_s2_fmlp_beauty_n0_s3.log 
    FMLP-Rec  Beauty               I10                  3     0.0536    0.0278  logs/run_s2_fmlp_beauty_i10_s3.log
    HSD       (SASRec)             Beauty               N0    2         0.0435  0.0201                            
    HSD       (SASRec)             Beauty               I10   2         0.0431  0.0201                            
    HSD       (SASRec)             Beauty               I20   2         0.0434  0.0202                            
    HSD       (SASRec)             Beauty               N0    3         0.0435  0.0201                            
    HSD       (SASRec)             Beauty               I10   3         0.0438  0.0209                            
    STEAM     Beauty               N0                   2     0.0629    0.0322  results/s2_steam_Beauty_N0_s2.json
    STEAM     Beauty               I10                  2     0.0574    0.0288  results/s2_steam_Beauty_I10_s2.jso
    STEAM     Beauty               I20                  2     0.0561    0.0289  results/s2_steam_Beauty_I20_s2.jso
    STEAM     Beauty               N0                   3     0.0629    0.0322  results/s2_steam_Beauty_N0_s3.json
    STEAM     Beauty               I10                  3     0.0596    0.0306  results/s2_steam_Beauty_I10_s3.jso
    FMLP-Rec  Sports_and_Outdoors  N0                   2     0.0306    0.0164  logs/run_s2_fmlp_sports_and_outdoo
    FMLP-Rec  Sports_and_Outdoors  I10                  2     0.0267    0.0136  logs/run_s2_fmlp_sports_and_outdoo
    FMLP-Rec  Sports_and_Outdoors  I20                  2     0.0267    0.0136  logs/run_s2_fmlp_sports_and_outdoo
    FMLP-Rec  Sports_and_Outdoors  N0                   3     0.0306    0.0164  logs/run_s2_fmlp_sports_and_outdoo
    FMLP-Rec  Sports_and_Outdoors  I10                  3     0.0289    0.0156  logs/run_s2_fmlp_sports_and_outdoo
    HSD       (SASRec)             Sports_and_Outdoors  N0    2         0.0214  0.0097                            
    HSD       (SASRec)             Sports_and_Outdoors  I10   2         0.0187  0.0085                            
    HSD       (SASRec)             Sports_and_Outdoors  I20   2         0.0185  0.0083                            
    HSD       (SASRec)             Sports_and_Outdoors  N0    3         0.0214  0.0097                            
    HSD       (SASRec)             Sports_and_Outdoors  I10   3         0.0208  0.0094                            
    STEAM     Sports_and_Outdoors  N0                   2     0.0390    0.0200  results/s2_steam_Sports_and_Outdoo
    STEAM     Sports_and_Outdoors  I10                  2     0.0351    0.0181  results/s2_steam_Sports_and_Outdoo
    STEAM     Sports_and_Outdoors  I20                  2     0.0344    0.0176  results/s2_steam_Sports_and_Outdoo
    STEAM     Sports_and_Outdoors  N0                   3     0.0390    0.0200  results/s2_steam_Sports_and_Outdoo
    FMLP-Rec  Yelp                 N0                   2     0.0256    0.0130  logs/run_s2_fmlp_yelp_n0_s2.log   
    FMLP-Rec  Yelp                 I10                  2     0.0269    0.0130  logs/run_s2_fmlp_yelp_i10_s2.log  
    FMLP-Rec  Yelp                 I20                  2     0.0260    0.0129  logs/run_s2_fmlp_yelp_i20_s2.log  
    FMLP-Rec  Yelp                 N0                   3     0.0256    0.0130  logs/run_s2_fmlp_yelp_n0_s3.log   
    HSD       (SASRec)             Yelp                 N0    2         0.0437  0.0287                            
    HSD       (SASRec)             Yelp                 I10   2         0.0441  0.0289                            
    HSD       (SASRec)             Yelp                 I20   2         0.0430  0.0284                            
    HSD       (SASRec)             Yelp                 N0    3         0.0437  0.0287                            
    STEAM     Yelp                 N0                   2     0.0627    0.0347  results/s2_steam_Yelp_N0_s2.json  
    STEAM     Yelp                 I10                  2     0.0600    0.0337  results/s2_steam_Yelp_I10_s2.json 
    STEAM     Yelp                 I20                  2     0.0550    0.0301  results/s2_steam_Yelp_I20_s2.json 
    STEAM     Yelp                 N0                   3     0.0627    0.0347  results/s2_steam_Yelp_N0_s3.json  
  run_summary.tsv (name, exit code, minutes, peak MiB):
    s2_fmlp_beauty_n0_s2	0	3	2557
    s2_hsd_beauty_n0_s2	0	7	7783
    s2_steam_beauty_n0_s2	0	101	22583
    s2_fmlp_sports_and_outdoors_n0_s2	0	6	2601
    s2_hsd_sports_and_outdoors_n0_s2	0	7	7763
    s2_steam_sports_and_outdoors_n0_s2	0	230	17493
    s2_fmlp_yelp_n0_s2	0	3	2599
    s2_hsd_yelp_n0_s2	0	15	7779
    s2_steam_yelp_n0_s2	0	212	18863
    s2_fmlp_beauty_i10_s2	0	3	2544
    s2_hsd_beauty_i10_s2	0	6	7764
    s2_steam_beauty_i10_s2	0	102	22562
    s2_fmlp_sports_and_outdoors_i10_s2	0	5	2569
    s2_hsd_sports_and_outdoors_i10_s2	0	6	7733
    s2_steam_sports_and_outdoors_i10_s2	0	231	17467
    s2_fmlp_yelp_i10_s2	0	6	2555
    s2_hsd_yelp_i10_s2	0	15	7747
    s2_steam_yelp_i10_s2	0	213	18831
    s2_fmlp_beauty_i20_s2	0	5	2525
    s2_hsd_beauty_i20_s2	0	5	7751
    s2_steam_beauty_i20_s2	0	103	22549
    s2_fmlp_sports_and_outdoors_i20_s2	0	7	2574
    s2_hsd_sports_and_outdoors_i20_s2	0	11	7733
    s2_steam_sports_and_outdoors_i20_s2	0	231	17460
    s2_fmlp_yelp_i20_s2	0	6	2529
    s2_hsd_yelp_i20_s2	0	17	7699
    s2_steam_yelp_i20_s2	0	213	18783
    s2_fmlp_beauty_n0_s3	0	3	3014
    s2_hsd_beauty_n0_s3	0	7	8224
    s2_steam_beauty_n0_s3	0	101	22705
    s2_fmlp_sports_and_outdoors_n0_s3	0	6	2557
    s2_hsd_sports_and_outdoors_n0_s3	0	7	7720
    s2_steam_sports_and_outdoors_n0_s3	0	230	17446
    s2_fmlp_yelp_n0_s3	0	3	2552
    s2_hsd_yelp_n0_s3	0	15	7732
    s2_steam_yelp_n0_s3	0	213	18820
    s2_fmlp_beauty_i10_s3	0	4	2510
    s2_hsd_beauty_i10_s3	0	6	7741
    s2_steam_beauty_i10_s3	0	102	22541
    s2_fmlp_sports_and_outdoors_i10_s3	0	6	2554
    s2_hsd_sports_and_outdoors_i10_s3	0	11	7720
---- queue log (~/survey_queue.log) ----
  2026-11-26 11:48:33   retry pass: failed jobs of configs/rq4/jobs_tune_here.csv, one at a time
  0 jobs to run, 273 already done
  2026-11-26 11:48:33 6 picks
  91 cells picked -> /home/anurag/survey/rq1/configs/rq4/best.json; incomplete: yelp|L1|drop (0/3), yelp|L1|reweight (0/3), yelp|L1|relabel (0/3), yelp|L1|resampl
  91 ml1m picks -> configs/rq4/picks_ml1m.json
  2026-11-26 11:48:33 7 finals [ml1m] seeds [all]
  831 of 837 jobs kept (datasets ml1m)
  0 jobs to run, 831 already done
  kept the logs of 0 failed jobs in logs/rq4_final/failed
  2026-11-26 11:48:33   retry pass: failed jobs of configs/rq4/jobs_final_ml1m.csv, one at a time
  0 jobs to run, 831 already done
  2026-11-26 11:48:33 RQ4 done [ml1m] seeds [all]
  2026-11-26 11:48:33 [pc2-queue] RQ4 ML-1M finished
  2026-11-26 11:48:33 [pc2-queue] RQ10 noise seed 2 (log ~/rq10_seeds.log, peer aura1@10.100.97.71)
  2026-11-26 11:48:37 [pc2-queue] PC2 queue complete: RQ4 ML-1M and RQ10 seed 2 finished
---- recent service log lines ----
2026-11-26T11:48:26+05:30 home systemd[1983]: Starting survey-kick.service - Start survey-queue if it is not running...
2026-11-26T11:48:26+05:30 home systemd[1983]: Started survey-queue.service - Survey unattended queue (pc2).
2026-11-26T11:48:26+05:30 home systemd[1983]: Finished survey-kick.service - Start survey-queue if it is not running.
2026-11-26T11:48:37+05:30 home systemd[1983]: survey-queue.service: Consumed 20.673s CPU time.
2026-11-26T12:07:26+05:30 home systemd[1983]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-26T12:07:31+05:30 home systemd[1983]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-26T12:07:31+05:30 home systemd[1983]: survey-snapshot.service: Consumed 1.040s CPU time.
2026-11-26T12:38:26+05:30 home systemd[1983]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
