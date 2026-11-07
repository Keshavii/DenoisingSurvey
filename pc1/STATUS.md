# pc1 status

```
pc1 (aura3@home)  2026-11-07 00:54:59 UTC  up since 2026-09-30 13:27:10
code 7f48e30 05 Nov 21:52  linger yes  disk free 1.2T  ram used 10/62 GB swap 0 GB 
gpu 100 %, 9009 MiB, 24564 MiB, 66
---- services ----
  partc-resume.service         active running
  partc.service                active running
  survey-queue.service         active running
  survey-snapshot.service      activating start
  last snapshot: 2026-11-07 00:25:01 push ok (00553f4; pc1)
---- gpu jobs ----
  4-08:01:57  python -u -m rq1kit.partc run --skip dcf,pld,sl
  31:36       bash -c python -m rq1kit.deca --C_1 10 --C_2 10 --alpha 1 --data data/amazon_book --train_file train.tsv --model lightg
  31:36       python -m rq1kit.deca --C_1 10 --C_2 10 --alpha 1 --data data/amazon_book --train_file train.tsv --model lightgcn --lr 
  20:42       bash -c python -m rq1kit.deca --C_1 10 --C_2 10 --alpha 1 --data data/amazon_book --train_file train_N2_20_s2.tsv --mod
  20:42       python -m rq1kit.deca --C_1 10 --C_2 10 --alpha 1 --data data/amazon_book --train_file train_N2_20_s2.tsv --model light
---- RQ1 Part C (partc driver status, refreshed every minute) ----
  status file written 2026-11-07 00:54:43
Part C status 2026-11-07 00:54  kit 7f48e30
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
DeCA     2 amazon_book           8/8   yes     3/9     2    0     0
DiffRec  2 adressa      passed   8/8   yes     6/6     0    0     0
DiffRec  2 ml1m                  8/8   yes     1/6     0    0     0
DiffRec  2 yelp                  8/8   yes     0/6     0    0     0
DiffRec  2 gowalla               8/8   yes     0/6     0    0     0
DiffRec  2 amazon_book           8/8   yes     0/6     0    0     0
RGCF     2 adressa      held     8/8   yes     6/6     0    0     0
RGCF     2 ml1m                  0/8   -       0/6     0    0     0
RGCF     2 yelp                  0/8   -       0/6     0    0     0
RGCF     2 gowalla               0/8   -       0/6     0    0     0
RGCF     2 amazon_book           0/8   -       0/6     0    0     0
SGL      2 adressa      passed   8/8   yes     6/6     0    0     0
SGL      2 ml1m                  8/8   yes     6/6     0    0     0
SGL      2 yelp                  8/8   yes     6/6     0    0     0
SGL      2 gowalla               8/8   yes     6/6     0    0     0
SGL      2 amazon_book           8/8   yes     0/6     0    0     0
LLaRD    3 ml1m         pending  0/8   -       0/6     0    0     0
total: 849 of 954 done, 2 running, 0 failed, 0 conflicts; held: rgcf
GPU: 100 %, 9009 MiB, 24564 MiB
rough finish: Mon 09 Nov 04:04 (51.2 h of known work)
  HELD     rgcf: canary valid NDCG@20 0.0777 < 0.0810 (0.5 x plain 0.1620)  (fix, then: partc retry rgcf)
---- RQ2 (after Part C) ----
  waits until Part C has nothing left to run
---- queue log (~/survey_queue.log) ----
  2026-11-06 22:34:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 22:44:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 22:54:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 23:04:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 23:14:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 23:24:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 23:34:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 23:44:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 23:54:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-07 00:04:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-07 00:14:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-07 00:24:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-07 00:34:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-07 00:44:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-07 00:54:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
---- recent service log lines ----
2026-11-06T22:55:01+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-06T23:24:58+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-06T23:25:01+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-06T23:54:58+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-06T23:55:02+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-07T00:24:58+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-07T00:25:01+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-07T00:54:58+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
