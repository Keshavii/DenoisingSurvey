# pc3 status

```
pc3 (aura1@aura-node1)  2026-11-05 21:02:38 UTC  up since 2026-11-03 22:15:42
code c440502 05 Nov 21:02  linger yes  disk free 103G  ram used 4/62 GB swap 1 GB 
gpu 0 %, 791 MiB, 24564 MiB, 42
---- services ----
  survey-queue.service         active running
  survey-snapshot.service      failed failed
  last snapshot: 2026-11-05 20:47:33 push FAILED after 3 tries (credentials? network?)
ALERT: GitHub snapshot is failing (see ~/survey_snapshot.log)
---- gpu jobs ----
---- RQ4 (signal x treatment) ----
  tune: not started
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
  2026-11-05 20:45:29 [pc3-queue] start, code c6d3c86
  2026-11-05 20:45:29 [pc3-queue] RQ10 re-runs complete
  2026-11-05 20:45:29 [pc3-queue] waiting for data/yelp from PC2 (see scripts/ops/README.md); next look in 10 min
  2026-11-05 20:55:29 [pc3-queue] waiting for data/yelp from PC2 (see scripts/ops/README.md); next look in 10 min
---- recent service log lines ----
2026-11-05T20:45:28+00:00 aura-node1 systemd[7943]: Started survey-snapshot.timer - Survey snapshot every 30 min.
2026-11-05T20:45:28+00:00 aura-node1 systemd[7943]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-05T20:45:29+00:00 aura-node1 systemd[7943]: Started survey-queue.service - Survey unattended queue (pc3).
2026-11-05T20:47:33+00:00 aura-node1 systemd[7943]: survey-snapshot.service: Main process exited, code=exited, status=1/FAILURE
2026-11-05T20:47:33+00:00 aura-node1 systemd[7943]: survey-snapshot.service: Failed with result 'exit-code'.
2026-11-05T20:47:33+00:00 aura-node1 systemd[7943]: Failed to start survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-05T20:47:33+00:00 aura-node1 systemd[7943]: survey-snapshot.service: Consumed 1.184s CPU time, 1.2M memory peak, 0B memory swap peak.
```
