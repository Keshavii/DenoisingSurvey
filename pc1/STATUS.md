# pc1 status

```
pc1 (aura3@home)  2026-11-07 05:55:00 UTC  up since 2026-09-30 13:27:10
code 7f48e30 05 Nov 21:52  linger yes  disk free 1.2T  ram used 10/62 GB swap 0 GB 
gpu 100 %, 12797 MiB, 24564 MiB, 67
---- services ----
  partc-resume.service         active running
  partc.service                active running
  survey-queue.service         active running
  survey-snapshot.service      activating start
  last snapshot: 2026-11-07 05:25:02 push ok (4b6cc9d; pc1)
---- gpu jobs ----
  4-13:01:57  python -u -m rq1kit.partc run --skip dcf,pld,sl
  02:18:53    bash -c python -m rq1kit.sgl --ssl_reg 0.1 --ssl_temp 0.2 --ssl_ratio 0.2 --data data/amazon_book --train_file train_N2
  02:18:53    python -m rq1kit.sgl --ssl_reg 0.1 --ssl_temp 0.2 --ssl_ratio 0.2 --data data/amazon_book --train_file train_N2_20_s1.t
  12:53       bash -c python -m rq1kit.sgl --ssl_reg 0.1 --ssl_temp 0.2 --ssl_ratio 0.2 --data data/amazon_book --train_file train.ts
  12:53       python -m rq1kit.sgl --ssl_reg 0.1 --ssl_temp 0.2 --ssl_ratio 0.2 --data data/amazon_book --train_file train.tsv --mode
---- RQ1 Part C (partc driver status, refreshed every minute) ----
  status file written 2026-11-07 05:54:20
Part C status 2026-11-07 05:54  kit 7f48e30
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
DiffRec  2 ml1m                  8/8   yes     1/6     0    0     0
DiffRec  2 yelp                  8/8   yes     6/6     0    0     0
DiffRec  2 gowalla               8/8   yes     6/6     0    0     0
DiffRec  2 amazon_book           8/8   yes     6/6     0    0     0
RGCF     2 adressa      held     8/8   yes     6/6     0    0     0
RGCF     2 ml1m                  0/8   -       0/6     0    0     0
RGCF     2 yelp                  0/8   -       0/6     0    0     0
RGCF     2 gowalla               0/8   -       0/6     0    0     0
RGCF     2 amazon_book           0/8   -       0/6     0    0     0
SGL      2 adressa      passed   8/8   yes     6/6     0    0     0
SGL      2 ml1m                  8/8   yes     6/6     0    0     0
SGL      2 yelp                  8/8   yes     6/6     0    0     0
SGL      2 gowalla               8/8   yes     6/6     0    0     0
SGL      2 amazon_book           8/8   yes     1/6     2    0     0
LLaRD    3 ml1m         pending  0/8   -       0/6     0    0     0
total: 874 of 954 done, 2 running, 0 failed, 0 conflicts; held: rgcf
GPU: 100 %, 12797 MiB, 24564 MiB
rough finish: Sun 08 Nov 10:00 (28.1 h of known work)
  HELD     rgcf: canary valid NDCG@20 0.0777 < 0.0810 (0.5 x plain 0.1620)  (fix, then: partc retry rgcf)
---- RQ2 (after Part C) ----
  waits until Part C has nothing left to run
---- queue log (~/survey_queue.log) ----
  2026-11-07 03:34:59 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-07 03:44:59 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-07 03:54:59 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-07 04:04:59 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-07 04:14:59 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-07 04:24:59 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-07 04:34:59 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-07 04:44:59 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-07 04:54:59 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-07 05:04:59 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-07 05:14:59 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-07 05:24:59 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-07 05:34:59 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-07 05:44:59 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-07 05:54:59 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
---- recent service log lines ----
2026-11-07T03:55:01+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-07T04:24:59+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-07T04:25:01+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-07T04:54:59+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-07T04:55:02+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-07T05:24:59+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-07T05:25:02+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-07T05:54:59+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
