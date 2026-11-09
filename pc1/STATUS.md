# pc1 status

```
pc1 (aura3@home)  2026-11-09 00:25:34 UTC  up since 2026-09-30 13:27:10
code 7f48e30 05 Nov 21:52  linger yes  disk free 1.1T  ram used 10/62 GB swap 0 GB 
gpu 41 %, 3841 MiB, 24564 MiB, 46
---- services ----
  partc.service                active running
  survey-queue.service         active running
  survey-snapshot.service      activating start
  last snapshot: 2026-11-08 23:55:22 push ok (3ec57d7; pc1)
---- gpu jobs ----
  1-06:20:17  python -u -m rq1kit.partc run --skip dcf,pld,sl
  00:10       python -m rq1kit.backbone --data data/amazon_book --train_file train_clean.tsv --model mf --loss bpr --lr 0.001 --reg 0
---- RQ1 Part C (partc driver status, refreshed every minute) ----
  status file written 2026-11-09 00:25:14
Part C status 2026-11-09 00:25  kit 7f48e30
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
GPU: 32 %, 2727 MiB, 24564 MiB
rough finish: Mon 09 Nov 00:25 (0.0 h of known work)
---- RQ2 (after Part C) ----
  started 2026-11-09 00:15:19
  rho*: adressa 0.607, ml1m 0.155, yelp 0.156, amazon_book 0.073
  rq2: not started
---- queue log (~/survey_queue.log) ----
  2026-11-08 23:35:19 [pc1-queue] waiting for Part C to finish (Part C running: 4; idle checks 0/3); next look in 10 min
  2026-11-08 23:45:19 [pc1-queue] waiting for Part C to finish (Part C running: 4; idle checks 0/3); next look in 10 min
  2026-11-08 23:55:19 [pc1-queue] waiting for Part C to finish (Part C running: 0; idle checks 1/3); next look in 10 min
  2026-11-09 00:05:19 [pc1-queue] waiting for Part C to finish (Part C running: 0; idle checks 2/3); next look in 10 min
  2026-11-09 00:15:19 [pc1-queue] Part C has nothing left to run: starting RQ2
  2026-11-09 00:15:20 [pc1-queue] RQ2 1/4 rho*
  adressa: rho* 0.6067, injection rate 1.5423 (254487 of 419491 rows)
  ml1m: rho* 0.1553, injection rate 0.1839 (124325 of 800309 rows)
  yelp: rho* 0.1558, injection rate 0.1846 (260581 of 1672520 rows)
  amazon_book: rho* 0.0735, injection rate 0.0793 (199475 of 2714021 rows)
  2026-11-09 00:15:21 [pc1-queue] RQ2 2/4 MF-BPR on the clean bases (top-K for N3)
  2026-11-09 00:15:21 [pc1-queue]   python -m rq1kit.backbone --data data/adressa --train_file train_clean.tsv --model mf --loss bpr --lr 0.005 --reg 1e-05 --seed
  2026-11-09 00:15:46 [pc1-queue]   python -m rq1kit.backbone --data data/ml1m --train_file train_clean.tsv --model mf --loss bpr --lr 0.001 --reg 0.01 --seed 1 -
  2026-11-09 00:17:43 [pc1-queue]   python -m rq1kit.backbone --data data/yelp --train_file train_clean.tsv --model mf --loss bpr --lr 0.001 --reg 0.01 --seed 1 -
  2026-11-09 00:25:23 [pc1-queue]   python -m rq1kit.backbone --data data/amazon_book --train_file train_clean.tsv --model mf --loss bpr --lr 0.001 --reg 0.01 --s
---- recent service log lines ----
2026-11-08T23:55:19+00:00 home systemd[3714]: partc-resume.service: Failed to open /run/user/1000/systemd/transient/partc-resume.service: No such file or directory
2026-11-08T23:55:19+00:00 home systemd[3714]: partc-resume.service: Failed to open /run/user/1000/systemd/transient/partc-resume.service: No such file or directory
2026-11-08T23:55:22+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-09T00:05:19+00:00 home systemd[3714]: partc-resume.service: Failed to open /run/user/1000/systemd/transient/partc-resume.service: No such file or directory
2026-11-09T00:05:19+00:00 home systemd[3714]: partc-resume.service: Failed to open /run/user/1000/systemd/transient/partc-resume.service: No such file or directory
2026-11-09T00:15:19+00:00 home systemd[3714]: partc-resume.service: Failed to open /run/user/1000/systemd/transient/partc-resume.service: No such file or directory
2026-11-09T00:15:19+00:00 home systemd[3714]: partc-resume.service: Failed to open /run/user/1000/systemd/transient/partc-resume.service: No such file or directory
2026-11-09T00:25:33+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
