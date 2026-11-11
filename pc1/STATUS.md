# pc1 status

```
pc1 (aura3@home)  2026-11-11 09:15:34 UTC  up since 2026-09-30 13:27:10
code 7f48e30 05 Nov 21:52  linger yes  disk free 1.1T  ram used 11/62 GB swap 0 GB 
gpu 98 %, 8398 MiB, 24564 MiB, 66
---- services ----
  partc.service                active running
  survey-queue.service         active running
  survey-snapshot.service      activating start
  last snapshot: 2026-11-11 08:44:36 push ok (ac60212; pc1)
---- gpu jobs ----
  3-15:10:17  python -u -m rq1kit.partc run --skip dcf,pld,sl
  02:37:55    bash -c python -m rq1kit.pld --begin_adv 5 --item_num 5 --temp 0.2 --data data/amazon_book --train_file train_RQ2N2_s1.
  02:37:55    python -m rq1kit.pld --begin_adv 5 --item_num 5 --temp 0.2 --data data/amazon_book --train_file train_RQ2N2_s1.tsv --mo
  01:01:18    bash -c python -m rq1kit.adt --method rce --alpha 0.05 --data data/amazon_book --train_file train_RQ2N2_s1.tsv --model 
  01:01:18    python -m rq1kit.adt --method rce --alpha 0.05 --data data/amazon_book --train_file train_RQ2N2_s1.tsv --model lightgcn
---- RQ1 Part C (partc driver status, refreshed every minute) ----
  status file written 2026-11-11 09:15:06
Part C status 2026-11-11 09:15  kit 7f48e30
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
GPU: 100 %, 8398 MiB, 24564 MiB   rq1kit.queue running (pids 2060000): partc shares the GPU, leaving it 4 slots
rough finish: Wed 11 Nov 09:15 (0.0 h of known work)
---- RQ2 (after Part C) ----
  started 2026-11-09 00:15:19
  rho*: adressa 0.607, ml1m 0.155, yelp 0.156, amazon_book 0.073
  rq2 adressa: 42/126 done, 0 failed so far, median 17 min/job, ~6 h left at 4 in parallel
  rq2 amazon_book: 18/126 done, 0 failed so far, median 175 min/job, ~158 h left at 2 in parallel
  rq2 ml1m: 42/126 done, 0 failed so far, median 21 min/job, ~7 h left at 4 in parallel
  rq2 yelp: 42/126 done, 0 failed so far, median 45 min/job, ~32 h left at 2 in parallel
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
2026-11-11T07:42:33+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-11T07:42:36+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-11T08:13:33+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-11T08:13:36+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-11T08:44:33+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-11T08:44:36+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-11T09:15:33+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
