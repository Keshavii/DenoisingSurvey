# pc1 status

```
pc1 (aura3@home)  2026-11-06 19:54:59 UTC  up since 2026-09-30 13:27:10
code 7f48e30 05 Nov 21:52  linger yes  disk free 1.2T  ram used 10/62 GB swap 0 GB 
gpu 100 %, 8495 MiB, 24564 MiB, 64
---- services ----
  partc-resume.service         active running
  partc.service                active running
  survey-queue.service         active running
  survey-snapshot.service      activating start
  last snapshot: 2026-11-06 19:25:01 push ok (a479eb4; pc1)
---- gpu jobs ----
  4-03:01:57  python -u -m rq1kit.partc run --skip dcf,pld,sl
  28:42       bash -c python -m rq1kit.ddrm --diff_lr 0.0001 --alpha 0.5 --steps 50 --data data/amazon_book --train_file train.tsv --
  28:42       python -m rq1kit.ddrm --diff_lr 0.0001 --alpha 0.5 --steps 50 --data data/amazon_book --train_file train.tsv --model li
  28:41       /home/aura3/miniconda3/envs/rq1/bin/python -m rq1kit.backbone --data data/amazon_book --train_file train.tsv --model li
  09:45       bash -c python -m rq1kit.ddrm --diff_lr 0.0001 --alpha 0.5 --steps 50 --data data/amazon_book --train_file train_N2_20_
  09:45       python -m rq1kit.ddrm --diff_lr 0.0001 --alpha 0.5 --steps 50 --data data/amazon_book --train_file train_N2_20_s3.tsv -
  09:45       /home/aura3/miniconda3/envs/rq1/bin/python -m rq1kit.backbone --data data/amazon_book --train_file train_N2_20_s3.tsv -
---- RQ1 Part C (partc driver status, refreshed every minute) ----
  status file written 2026-11-06 19:54:06
Part C status 2026-11-06 19:54  kit 7f48e30
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
DDRM     2 amazon_book           8/8   yes     4/6     2    0     0
DeCA     2 adressa      passed   8/8   yes     9/9     0    0     0
DeCA     2 ml1m                  8/8   yes     9/9     0    0     0
DeCA     2 yelp                  8/8   yes     0/9     0    0     0
DeCA     2 gowalla               8/8   yes     0/9     0    0     0
DeCA     2 amazon_book           8/8   yes     0/9     0    0     0
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
total: 826 of 954 done, 2 running, 0 failed, 0 conflicts; held: rgcf
GPU: 99 %, 8495 MiB, 24564 MiB
rough finish: Mon 09 Nov 10:31 (62.6 h of known work)
  HELD     rgcf: canary valid NDCG@20 0.0777 < 0.0810 (0.5 x plain 0.1620)  (fix, then: partc retry rgcf)
---- RQ2 (after Part C) ----
  waits until Part C has nothing left to run
---- queue log (~/survey_queue.log) ----
  2026-11-06 17:34:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 17:44:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 17:54:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 18:04:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 18:14:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 18:24:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 18:34:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 18:44:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 18:54:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 19:04:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 19:14:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 19:24:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 19:34:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 19:44:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
  2026-11-06 19:54:58 [pc1-queue] waiting for Part C to finish (partc-resume has not restarted partc yet; idle checks 0/3); next look in 10 min
---- recent service log lines ----
2026-11-06T17:55:01+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-06T18:24:58+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-06T18:25:01+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-06T18:54:58+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-06T18:55:01+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-06T19:24:58+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-06T19:25:01+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-06T19:54:58+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
