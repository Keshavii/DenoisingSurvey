# pc1 status

```
pc1 (aura3@home)  2026-11-20 11:40:34 UTC  up since 2026-09-30 13:27:10
code 7f48e300 05 Nov 21:52  linger yes  disk free 1.1T  ram used 6/62 GB swap 0 GB 
gpu 0 %, 642 MiB, 24564 MiB, 42
---- services ----
  partc.service                active running
  survey-queue.service         inactive dead
  survey-snapshot.service      activating start
  last snapshot: 2026-11-20 11:09:36 push ok (77a67f36; pc1)
---- gpu jobs ----
  12-17:35:17 python -u -m rq1kit.partc run --skip dcf,pld,sl
---- RQ1 Part C (partc driver status, refreshed every minute) ----
  status file written 2026-11-20 11:40:11
Part C status 2026-11-20 11:40  kit 7f48e300
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
GPU: 0 %, 642 MiB, 24564 MiB
rough finish: Fri 20 Nov 11:40 (0.0 h of known work)
---- RQ2 (after Part C) ----
  started 2026-11-09 00:15:19
  rho*: adressa 0.607, ml1m 0.155, yelp 0.156, amazon_book 0.073
  rq2 adressa: 126/126 done, 0 failed so far
  rq2 amazon_book: 126/126 done, 0 failed so far
  rq2 ml1m: 126/126 done, 0 failed so far
  rq2 yelp: 126/126 done, 0 failed so far
---- queue log (~/survey_queue.log) ----
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
  2026-11-20 03:32:19 [pc1-queue]   retry pass: failed RQ2 jobs, one at a time
  0 jobs to run, 504 already done
  2026-11-20 03:32:19 [pc1-queue] PC1 queue complete: RQ2 finished (results/RQ2)
---- recent service log lines ----
2026-11-20T10:07:33+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-20T10:07:36+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-20T10:38:33+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-20T10:38:37+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-20T11:09:33+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-20T11:09:36+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-20T11:40:33+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
