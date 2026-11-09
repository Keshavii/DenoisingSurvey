# pc1 status

```
pc1 (aura3@home)  2026-11-09 09:12:34 UTC  up since 2026-09-30 13:27:10
code 7f48e30 05 Nov 21:52  linger yes  disk free 1.1T  ram used 11/62 GB swap 0 GB 
gpu 100 %, 6862 MiB, 24564 MiB, 67
---- services ----
  partc.service                active running
  survey-queue.service         active running
  survey-snapshot.service      activating start
  last snapshot: 2026-11-09 08:41:36 push ok (d08aaf0; pc1)
---- gpu jobs ----
  1-15:07:17  python -u -m rq1kit.partc run --skip dcf,pld,sl
  58:28       bash -c python -m rq1kit.drrl --loss sl --lr_mult 10 --ssm_temp 0.12 --data data/ml1m --train_file train_RQ2N3_s1.tsv -
  58:28       python -m rq1kit.drrl --loss sl --lr_mult 10 --ssm_temp 0.12 --data data/ml1m --train_file train_RQ2N3_s1.tsv --model l
  23:36       bash -c python -m rq1kit.rgcf --lr_mult 0.1 --prune_threshold 0.02 --MIM_weight 1e-06 --data data/ml1m --train_file tra
  23:36       python -m rq1kit.rgcf --lr_mult 0.1 --prune_threshold 0.02 --MIM_weight 1e-06 --data data/ml1m --train_file train_RQ2N3
  11:52       bash -c python -m rq1kit.sgl --ssl_reg 0.05 --ssl_temp 0.5 --ssl_ratio 0.1 --data data/ml1m --train_file train_RQ2N3_s1
  11:52       python -m rq1kit.sgl --ssl_reg 0.05 --ssl_temp 0.5 --ssl_ratio 0.1 --data data/ml1m --train_file train_RQ2N3_s1.tsv --m
---- RQ1 Part C (partc driver status, refreshed every minute) ----
  status file written 2026-11-09 09:12:19
Part C status 2026-11-09 09:12  kit 7f48e30
method   b dataset      canary  tune   pick  finals  run fail confl
DCF      1 adressa      passed   8/8   yes     9/9     0    0     0
DCF      1 ml1m                  8/8   yes     9/9     0    0     0
DCF      1 yelp                  8/8   yes     9/9     0    0     0
DCF      1 gowalla               8/8   yes     9/9     0    0     0
DCF      1 amazon_book           8/8   yes     9/9     0    0     0
DrRL     1 adressa      passed   8/8   yes     9/9     0    0     0
DrRL     1 ml1m                  8/8   yes     9/9     0    0     0
DrRL     1 yelp                  8/8   yes     9/9     0    0     0
DrRL     1 gowalla               8/8   yes     9/9     0    0     0
DrRL     1 amazon_book           8/8   yes     9/9     0    0     0
PLD      1 adressa      passed   8/8   yes     9/9     0    0     0
PLD      1 ml1m                  8/8   yes     9/9     0    0     0
PLD      1 yelp                  8/8   yes     9/9     0    0     0
PLD      1 gowalla               8/8   yes     9/9     0    0     0
PLD      1 amazon_book           8/8   yes     9/9     0    0     0
R-CE     1 adressa      passed   7/7   yes     9/9     0    0     0
R-CE     1 ml1m                  7/7   yes     9/9     0    0     0
R-CE     1 yelp                  7/7   yes     9/9     0    0     0
R-CE     1 gowalla               7/7   yes     9/9     0    0     0
R-CE     1 amazon_book           7/7   yes     9/9     0    0     0
Plain-SL 1 adressa      passed   8/8   yes     9/9     0    0     0
Plain-SL 1 ml1m                  8/8   yes     9/9     0    0     0
Plain-SL 1 yelp                  8/8   yes     9/9     0    0     0
Plain-SL 1 gowalla               8/8   yes     9/9     0    0     0
Plain-SL 1 amazon_book           8/8   yes     9/9     0    0     0
T-CE     1 adressa      passed   8/8   yes     9/9     0    0     0
T-CE     1 ml1m                  8/8   yes     9/9     0    0     0
T-CE     1 yelp                  8/8   yes     9/9     0    0     0
T-CE     1 gowalla               8/8   yes     9/9     0    0     0
T-CE     1 amazon_book           8/8   yes     9/9     0    0     0
BOD      2 adressa      passed   8/8   yes     6/6     0    0     0
BOD      2 ml1m                  8/8   yes     6/6     0    0     0
BOD      2 yelp                  8/8   yes     6/6     0    0     0
BOD      2 gowalla               8/8   yes     6/6     0    0     0
BOD      2 amazon_book           8/8   yes     6/6     0    0     0
DDRM     2 adressa      passed   8/8   yes     6/6     0    0     0
DDRM     2 ml1m                  8/8   yes     6/6     0    0     0
DDRM     2 yelp                  8/8   yes     6/6     0    0     0
DDRM     2 gowalla               8/8   yes     6/6     0    0     0
DDRM     2 amazon_book           8/8   yes     6/6     0    0     0
DeCA     2 adressa      passed   8/8   yes     9/9     0    0     0
DeCA     2 ml1m                  8/8   yes     9/9     0    0     0
DeCA     2 yelp                  8/8   yes     9/9     0    0     0
DeCA     2 gowalla               8/8   yes     9/9     0    0     0
DeCA     2 amazon_book           8/8   yes     9/9     0    0     0
DiffRec  2 adressa      passed   8/8   yes     6/6     0    0     0
DiffRec  2 ml1m                  8/8   yes     6/6     0    0     0
DiffRec  2 yelp                  8/8   yes     6/6     0    0     0
DiffRec  2 gowalla               8/8   yes     6/6     0    0     0
DiffRec  2 amazon_book           8/8   yes     6/6     0    0     0
RGCF     2 adressa      passed   8/8   yes     6/6     0    0     0
RGCF     2 ml1m                  8/8   yes     6/6     0    0     0
RGCF     2 yelp                  8/8   yes     6/6     0    0     0
RGCF     2 gowalla               8/8   yes     6/6     0    0     0
RGCF     2 amazon_book           8/8   yes     6/6     0    0     0
SGL      2 adressa      passed   8/8   yes     6/6     0    0     0
SGL      2 ml1m                  8/8   yes     6/6     0    0     0
SGL      2 yelp                  8/8   yes     6/6     0    0     0
SGL      2 gowalla               8/8   yes     6/6     0    0     0
SGL      2 amazon_book           8/8   yes     6/6     0    0     0
LLaRD    3 ml1m         passed   8/8   yes     6/6     0    0     0
total: 954 of 954 done, 0 running, 0 failed, 0 conflicts; held: none
GPU: 100 %, 6862 MiB, 24564 MiB   rq1kit.queue running (pids 2060000): partc shares the GPU, leaving it 4 slots
rough finish: Mon 09 Nov 09:12 (0.0 h of known work)
---- RQ2 (after Part C) ----
  started 2026-11-09 00:15:19
  rho*: adressa 0.607, ml1m 0.155, yelp 0.156, amazon_book 0.073
  rq2 adressa: 42/126 done, 0 failed so far, median 17 min/job, ~6 h left at 4 in parallel
  rq2 amazon_book: 0/126 done, 0 failed so far
  rq2 ml1m: 39/126 done, 0 failed so far, median 20 min/job, ~7 h left at 4 in parallel
  rq2 yelp: 0/126 done, 0 failed so far
---- queue log (~/survey_queue.log) ----
  yelp N3 s1: 257378 injected = 0.1542 of 1669317 rows (rho* 0.1558)
  yelp N3 s2: 257318 injected = 0.1542 of 1669257 rows (rho* 0.1558)
  yelp N3 s3: 257369 injected = 0.1542 of 1669308 rows (rho* 0.1558)
  amazon_book N1 s1: 199376 injected = 0.0735 of 2713922 rows (rho* 0.0735)
  amazon_book N1 s2: 199500 injected = 0.0735 of 2714046 rows (rho* 0.0735)
  amazon_book N1 s3: 199414 injected = 0.0735 of 2713960 rows (rho* 0.0735)
  amazon_book N2 s1: 199376 injected = 0.0735 of 2713922 rows (rho* 0.0735)
  amazon_book N2 s2: 199500 injected = 0.0735 of 2714046 rows (rho* 0.0735)
  amazon_book N2 s3: 199414 injected = 0.0735 of 2713960 rows (rho* 0.0735)
  amazon_book N3 s1: 197845 injected = 0.0729 of 2712391 rows (rho* 0.0735)
  amazon_book N3 s2: 197973 injected = 0.0730 of 2712519 rows (rho* 0.0735)
  amazon_book N3 s3: 197883 injected = 0.0730 of 2712429 rows (rho* 0.0735)
  2026-11-09 00:55:00 [pc1-queue] RQ2 4/4 runs
  504 RQ2 jobs
  504 jobs to run, 0 already done
---- recent service log lines ----
2026-11-09T07:39:33+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-09T07:39:36+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-09T08:10:33+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-09T08:10:36+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-09T08:41:33+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-09T08:41:36+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-09T09:12:33+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
