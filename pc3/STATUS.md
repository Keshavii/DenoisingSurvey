# pc3 status

```
pc3 (aura1@aura-node1)  2026-11-07 23:26:43 UTC  up since 2026-11-03 22:15:42
code 7f48e30 05 Nov 21:52  linger yes  disk free 97G  ram used 9/62 GB swap 1 GB 
gpu 100 %, 4996 MiB, 24564 MiB, 66
---- services ----
  survey-queue.service         active running
  survey-snapshot.service      activating start
  last snapshot: 2026-11-07 22:56:43 staged /home/aura1/survey-status/pc3 for relay (this PC has no GitHub login; a relaying PC pushes it)
---- gpu jobs ----
  34:13       python -m rq1kit.rq4 --signal M1 --treat graph_reweight --beta 0.5 --data data/yelp --lr 0.005 --reg 0.001 --epochs 100
  21:53       python -m rq1kit.rq4 --signal M1 --treat graph_reweight --beta 1.0 --data data/yelp --lr 0.005 --reg 0.001 --epochs 100
---- RQ4 (signal x treatment) ----
  tune yelp: 172/249 done, 0 failed so far, median 37 min/job, ~23 h left at 2 in parallel
  final: not started
---- RQ10 (specialists) ----
  .done markers: 19  (gbsr_yelp_r2 fmlp_beauty gbsr_epinions_r1 fmlp_beauty_n0 hdsr_default steam_beauty gbsr_douban_r1 repro_fmlp fmlp_beauty_n2_20 steam_beauty_n2_20 gbsr_douban_r2 repro_gbsr fmlp_beauty_n3_30 steam_beauty_n3_30 repro_preferdiff gbsr_epinions_r2 steam_beauty_n0 gbsr_yelp_r1 repro_steam )
  last lines of ~/rq10_rerun.log:
    hsd_sports_sasrec     1  16   7827
    hsd_yelp_sasrec       1  9    7809
    hsd_beauty_sasrec     1  8    7843
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
---- queue log (~/survey_queue.log) ----
  2026-11-05 21:19:43 RQ4 start: datasets [yelp], tune 1, final seeds [all], picks from this PC
  2026-11-05 21:19:43 1 clean base and MF-BPR on it
  2026-11-05 21:19:43 2 noise files
  2026-11-05 21:19:43 4b reference models for the clean bases (teacher M1c) and the Yelp files (R2, M1, hard positives)
  2026-11-05 21:19:47 5 tuning [yelp]
  249 of 522 jobs kept (datasets yelp)
  2026-11-05 21:32:53 [pc3-queue] start, code dedb518
  2026-11-05 21:32:53 [pc3-queue] RQ10 re-runs complete
  2026-11-05 21:32:53 RQ4 start: datasets [yelp], tune 1, final seeds [all], picks from this PC
  2026-11-05 21:32:53 1 clean base and MF-BPR on it
  2026-11-05 21:32:53 2 noise files
  2026-11-05 21:32:53 4b reference models for the clean bases (teacher M1c) and the Yelp files (R2, M1, hard positives)
  2026-11-05 21:32:56 5 tuning [yelp]
  249 of 522 jobs kept (datasets yelp)
  249 jobs to run, 0 already done
---- recent service log lines ----
2026-11-07T21:56:42+00:00 aura-node1 systemd[7943]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-07T21:56:42+00:00 aura-node1 systemd[7943]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-07T22:26:42+00:00 aura-node1 systemd[7943]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-07T22:26:43+00:00 aura-node1 systemd[7943]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-07T22:56:43+00:00 aura-node1 systemd[7943]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-07T22:56:43+00:00 aura-node1 systemd[7943]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-07T23:26:43+00:00 aura-node1 systemd[7943]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
