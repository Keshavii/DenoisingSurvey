# pc1 status

```
pc1 (aura3@home)  2026-11-22 16:21:34 UTC  up since 2026-09-30 13:27:10
code 2b25825f 21 Nov 18:28  linger yes  disk free 1.1T  ram used 9/62 GB swap 0 GB 
gpu 95 %, 4662 MiB, 24564 MiB, 65
---- services ----
  partc.service                active running
  survey-kick.service          inactive dead
  survey-queue.service         active running
  survey-snapshot.service      activating start
  last snapshot: 2026-11-22 15:50:36 push ok (0142ad5a; pc1)
---- gpu jobs ----
  14-22:16:17 python -u -m rq1kit.partc run --skip dcf,pld,sl
  09:14       bash -c python -m rq1kit.backbone --loss bce --data data/gowalla --train_file train_RQ5N2_50_s1.tsv --model lightgcn --
  09:14       python -m rq1kit.backbone --loss bce --data data/gowalla --train_file train_RQ5N2_50_s1.tsv --model lightgcn --lr 0.005
  03:29       bash -c python -m rq1kit.dcf --drop_rate 0.2 --num_gradual 30000 --time_step 3 --schedule_epochs 100 --relabel_ratio 0.
  03:29       python -m rq1kit.dcf --drop_rate 0.2 --num_gradual 30000 --time_step 3 --schedule_epochs 100 --relabel_ratio 0.09 --co_
---- RQ1 Part C (partc driver status, refreshed every minute) ----
  status file written 2026-11-22 16:21:01
Part C status 2026-11-22 16:21  kit 2b25825f
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
GPU: 100 %, 4662 MiB, 24564 MiB   rq1kit.queue running (pids 3758135): partc shares the GPU, leaving it 4 slots
rough finish: Sun 22 Nov 16:21 (0.0 h of known work)
---- RQ2 (after Part C) ----
  started 2026-11-09 00:15:19
  rho*: adressa 0.607, ml1m 0.155, yelp 0.156, amazon_book 0.073
  rq2 adressa: 126/126 done, 0 failed so far
  rq2 amazon_book: 126/126 done, 0 failed so far
  rq2 ml1m: 126/126 done, 0 failed so far
  rq2 yelp: 126/126 done, 0 failed so far
---- RQ5 (noise curves, Yelp and Gowalla) ----
  rq5 gowalla: 29/126 done, 0 failed so far, median 14 min/job, ~11 h left at 2 in parallel
  rq5 yelp: 42/126 done, 0 failed so far, median 43 min/job, ~30 h left at 2 in parallel
---- queue log (~/survey_queue.log) ----
  yelp N2 50% s1: 705883 injected = 0.3333 of 2117822 rows
  yelp N2 50% s2: 706003 injected = 0.3333 of 2117942 rows
  yelp N2 50% s3: 706002 injected = 0.3333 of 2117941 rows
  gowalla N2 10% s1: 82219 injected = 0.0909 of 904697 rows
  gowalla N2 10% s2: 82294 injected = 0.0910 of 904772 rows
  gowalla N2 10% s3: 82291 injected = 0.0910 of 904769 rows
  gowalla N2 30% s1: 246715 injected = 0.2307 of 1069193 rows
  gowalla N2 30% s2: 246772 injected = 0.2308 of 1069250 rows
  gowalla N2 30% s3: 246677 injected = 0.2307 of 1069155 rows
  gowalla N2 50% s1: 411216 injected = 0.3333 of 1233694 rows
  gowalla N2 50% s2: 411305 injected = 0.3334 of 1233783 rows
  gowalla N2 50% s3: 411245 injected = 0.3333 of 1233723 rows
  2026-11-21 18:30:53 [pc1-queue] RQ5 2/2 runs
  252 RQ5 jobs
  252 jobs to run, 0 already done
---- recent service log lines ----
2026-11-22T14:36:33+00:00 home systemd[3714]: Finished survey-kick.service - Start survey-queue if it is not running.
2026-11-22T14:48:33+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-22T14:48:37+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-22T15:19:33+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-22T15:19:36+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-22T15:50:33+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-22T15:50:36+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-22T16:21:33+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
