# pc3 status

```
pc3 (aura1@aura-node1)  2026-11-09 12:57:08 UTC  up since 2026-11-03 22:15:42
code 7f48e30 05 Nov 21:52  linger yes  disk free 85G  ram used 10/62 GB swap 1 GB 
gpu 99 %, 5244 MiB, 24564 MiB, 67
---- services ----
  survey-queue.service         active running
  survey-snapshot.service      activating start
  last snapshot: 2026-11-09 12:27:08 staged /home/aura1/survey-status/pc3 for relay (this PC has no GitHub login; a relaying PC pushes it)
---- gpu jobs ----
  30:43       bash -c python -m rq1kit.rq4 --signal M1c --treat resample --temp 0.2 --data data/yelp --train_file train.tsv --lr 0.00
  30:43       python -m rq1kit.rq4 --signal M1c --treat resample --temp 0.2 --data data/yelp --train_file train.tsv --lr 0.005 --reg 
  23:38       bash -c python -m rq1kit.rq4 --signal L2 --treat drop --rate 0.05 --data data/yelp --train_file train.tsv --lr 0.005 --
  23:38       python -m rq1kit.rq4 --signal L2 --treat drop --rate 0.05 --data data/yelp --train_file train.tsv --lr 0.005 --reg 0.00
---- RQ4 (signal x treatment) ----
  tune yelp: 249/249 done, 0 failed so far
  picks: picks_yelp.json (83 cells)
  final yelp: 16/169 done, 0 failed so far, median 50 min/job, ~64 h left at 2 in parallel
---- RQ10 (specialists) ----
  .done markers: 35  (hsd_sports_sasrec gbsr_yelp_r2 fmlp_beauty gbsr_epinions_r1 s2_fmlp_beauty_i20_s1 fmlp_beauty_n0 hdsr_default s2_hsd_beauty_i20_s1 s2_hsd_beauty_n0_s1 s2_steam_beauty_i10_s1 steam_beauty gbsr_douban_r1 repro_fmlp hsd_beauty_sasrec steam_beauty_n2_20 s2_fmlp_sports_and_outdoors_i20_s1 s2_fmlp_beauty_n0_s1 gbsr_douban_r2 repro_gbsr steam_beauty_n3_30 repro_preferdiff gbsr_epinions_r2 s2_hsd_sports_and_outdoors_i10_s1 steam_beauty_n0 gbsr_yelp_r1 s2_steam_beauty_i20_s1 s2_fmlp_sports_and_outdoors_n0_s1 s2_steam_beauty_n0_s1 hsd_yelp_sasrec s2_hsd_sports_and_outdoors_i20_s1 repro_steam s2_hsd_sports_and_outdoors_n0_s1 s2_fmlp_beauty_i10_s1 s2_hsd_beauty_i10_s1 s2_fmlp_sports_and_outdoors_i10_s1 )
  last lines of ~/rq10_stage1.log:
      HSD (SASRec)  Sports_and_Outdoors  I20  s1  Recall@10 0.0193  NDCG@10 0.0089
    2026-11-09 05:43:07 [rq10-stage2] stage 2 complete: 15 runs with results (table: /home/aura1/survey/rq10/results/stage2_summary.tsv)
    2026-11-09 05:43:07 [rq10-stage1] stage 1 complete: 3 of 10 jobs have results; without: gdmsr_yelp gdmsr_ciao gdmsr_douban steam_sports stea
  stage 2 (full ranking, Recall@10 / NDCG@10):
    method    dataset              level                seed  recall10  ndcg10  source                            
    FMLP-Rec  Beauty               N0                   1     0.0562    0.0294  logs/run_s2_fmlp_beauty_n0_s1.log 
    FMLP-Rec  Beauty               I10                  1     0.0527    0.0274  logs/run_s2_fmlp_beauty_i10_s1.log
    FMLP-Rec  Beauty               I20                  1     0.0511    0.0269  logs/run_s2_fmlp_beauty_i20_s1.log
    HSD       (SASRec)             Beauty               N0    1         0.0435  0.0201                            
    HSD       (SASRec)             Beauty               I10   1         0.0418  0.0195                            
    HSD       (SASRec)             Beauty               I20   1         0.0424  0.0197                            
    STEAM     Beauty               N0                   1     0.0629    0.0322  results/s2_steam_Beauty_N0_s1.json
    STEAM     Beauty               I10                  1     0.0601    0.0305  results/s2_steam_Beauty_I10_s1.jso
    STEAM     Beauty               I20                  1     0.0561    0.0278  results/s2_steam_Beauty_I20_s1.jso
    FMLP-Rec  Sports_and_Outdoors  N0                   1     0.0310    0.0172  logs/run_s2_fmlp_sports_and_outdoo
    FMLP-Rec  Sports_and_Outdoors  I10                  1     0.0283    0.0145  logs/run_s2_fmlp_sports_and_outdoo
    FMLP-Rec  Sports_and_Outdoors  I20                  1     0.0243    0.0125  logs/run_s2_fmlp_sports_and_outdoo
    HSD       (SASRec)             Sports_and_Outdoors  N0    1         0.0223  0.0108                            
    HSD       (SASRec)             Sports_and_Outdoors  I10   1         0.0204  0.0091                            
    HSD       (SASRec)             Sports_and_Outdoors  I20   1         0.0193  0.0089                            
  run_summary.tsv (name, exit code, minutes, peak MiB):
    gbsr_douban_r1	0	8	3642
    gbsr_epinions_r1	0	8	20896
    gbsr_yelp_r1	0	12	11993
    hsd_beauty_sasrec	1	15	11981
    gbsr_douban_r2	0	11	10986
    gbsr_epinions_r2	0	9	11823
    gbsr_yelp_r2	0	13	11924
    hdsr_default	0	6	9675
    gdmsr_yelp	1	0	8032
    gdmsr_ciao	1	0	8032
    gdmsr_douban	1	0	8032
    steam_beauty	1	0	8040
    steam_sports	1	0	8032
    steam_yelp	1	0	8032
    fmlp_beauty	1	1	23821
    fmlp_sports	1	0	8563
    hsd_sports_sasrec	1	30	11924
    fmlp_yelp	1	0	8631
    preferdiff_beauty	1	0	11311
    hsd_yelp_sasrec	1	25	11311
    ssdrec_beauty_sasrec	1	10	687
    ssdrec_sports_sasrec	1	34	679
    ssdrec_yelp_sasrec	1	12	501
    gdmsr_yelp	1	0	759
    gdmsr_ciao	1	0	753
    gdmsr_douban	1	0	769
    steam_beauty	0	129	22989
    steam_sports	1	0	464
    steam_yelp	1	0	464
    steam_beauty_n0	0	129	22636
    steam_beauty_n2_20	0	129	22641
    steam_beauty_n3_30	0	129	22641
    steam_sports_n0	1	0	469
    steam_sports_n2_20	1	0	469
    steam_sports_n3_30	1	0	469
    steam_yelp_n0	1	0	469
    steam_yelp_n2_20	1	0	469
    steam_yelp_n3_30	1	0	469
    fmlp_beauty	0	3	2617
    preferdiff_beauty	1	0	469
    hsd_sports_sasrec	1	16	7827
    hsd_yelp_sasrec	1	9	7809
    hsd_beauty_sasrec	1	8	7843
    gdmsr_yelp	1	0	2041
    gdmsr_ciao	1	0	507
    gdmsr_douban	1	0	507
    steam_sports	1	0	507
    steam_yelp	1	0	507
    hsd_beauty_sasrec	0	8	7881
    hsd_sports_sasrec	0	16	7865
    hsd_yelp_sasrec	0	9	7847
    s2_fmlp_beauty_n0_s1	0	3	2655
    s2_hsd_beauty_n0_s1	0	8	7881
    s2_steam_beauty_n0_s1	0	102	22679
    s2_fmlp_sports_and_outdoors_n0_s1	0	6	2713
    s2_hsd_sports_and_outdoors_n0_s1	0	6	7859
    s2_steam_sports_and_outdoors_n0_s1	1	0	507
    s2_fmlp_beauty_i10_s1	0	4	2665
    s2_hsd_beauty_i10_s1	0	10	7881
    s2_steam_beauty_i10_s1	0	103	22679
    s2_fmlp_sports_and_outdoors_i10_s1	0	8	2699
    s2_hsd_sports_and_outdoors_i10_s1	0	10	7863
    s2_steam_sports_and_outdoors_i10_s1	1	0	507
    s2_fmlp_beauty_i20_s1	0	5	2655
    s2_hsd_beauty_i20_s1	0	9	7881
    s2_steam_beauty_i20_s1	0	103	22679
    s2_fmlp_sports_and_outdoors_i20_s1	0	6	2699
    s2_hsd_sports_and_outdoors_i20_s1	0	19	7865
    s2_steam_sports_and_outdoors_i20_s1	1	0	507
---- queue log (~/survey_queue.log) ----
  2026-11-08 22:17:58 [pc3-queue] RQ10 stage 1 (log ~/rq10_stage1.log)
  2026-11-09 05:43:07 RQ4 start: datasets [yelp], tune 1, final seeds [1], picks from this PC
  2026-11-09 05:43:07 1 clean base and MF-BPR on it
  2026-11-09 05:43:07 2 noise files
  2026-11-09 05:43:07 4b reference models for the clean bases (teacher M1c) and the Yelp files (R2, M1, hard positives)
  2026-11-09 05:43:11 5 tuning [yelp]
  249 of 522 jobs kept (datasets yelp)
  0 jobs to run, 249 already done
  2026-11-09 05:43:11   retry pass: failed jobs of configs/rq4/jobs_tune_here.csv, one at a time
  0 jobs to run, 249 already done
  2026-11-09 05:43:11 6 picks
  83 cells picked -> /home/aura1/survey/rq1/configs/rq4/best.json; incomplete: ml1m|L1|drop (0/3), ml1m|L1|reweight (0/3), ml1m|L1|relabel (0/3), ml1m|L1|resample
  83 yelp picks -> configs/rq4/picks_yelp.json
  2026-11-09 05:43:11 7 finals [yelp] seeds [1]
  169 of 350 jobs kept (datasets yelp, seeds 1)
---- recent service log lines ----
2026-11-09T11:27:07+00:00 aura-node1 systemd[7943]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-09T11:27:08+00:00 aura-node1 systemd[7943]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-09T11:57:08+00:00 aura-node1 systemd[7943]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-09T11:57:08+00:00 aura-node1 systemd[7943]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-09T12:27:08+00:00 aura-node1 systemd[7943]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-09T12:27:08+00:00 aura-node1 systemd[7943]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-09T12:57:08+00:00 aura-node1 systemd[7943]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
