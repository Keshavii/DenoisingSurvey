# pc1 status

```
pc1 (aura3@home)  2026-11-08 15:25:14 UTC  up since 2026-09-30 13:27:10
code 7f48e30 05 Nov 21:52  linger yes  disk free 1.2T  ram used 10/62 GB swap 0 GB 
gpu 100 %, 14543 MiB, 24564 MiB, 68
---- services ----
  partc.service                active running
  survey-queue.service         active running
  survey-snapshot.service      activating start
  last snapshot: 2026-11-08 14:55:16 push ok (d0434ba; pc1)
---- gpu jobs ----
  21:19:57    python -u -m rq1kit.partc run --skip dcf,pld,sl
  29:19       bash -c python -m rq1kit.rgcf --lr_mult 0.1 --prune_threshold 0.06 --MIM_weight 1e-05 --data data/yelp --train_file tra
  29:19       python -m rq1kit.rgcf --lr_mult 0.1 --prune_threshold 0.06 --MIM_weight 1e-05 --data data/yelp --train_file train_N2_20
  09:22       bash -c python -m rq1kit.rgcf --lr_mult 0.1 --prune_threshold 0.06 --MIM_weight 1e-05 --data data/yelp --train_file tra
  09:22       python -m rq1kit.rgcf --lr_mult 0.1 --prune_threshold 0.06 --MIM_weight 1e-05 --data data/yelp --train_file train.tsv -
---- RQ1 Part C (partc driver status, refreshed every minute) ----
  status file written 2026-11-08 15:24:14
Part C status 2026-11-08 15:24  kit 7f48e30
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
RGCF     2 ml1m                  8/8   yes     0/6     0    0     0
RGCF     2 yelp                  8/8   yes     3/6     2    0     0
RGCF     2 gowalla               8/8   yes     0/6     0    0     0
RGCF     2 amazon_book           8/8   yes     0/6     0    0     0
SGL      2 adressa      passed   8/8   yes     6/6     0    0     0
SGL      2 ml1m                  8/8   yes     6/6     0    0     0
SGL      2 yelp                  8/8   yes     6/6     0    0     0
SGL      2 gowalla               8/8   yes     6/6     0    0     0
SGL      2 amazon_book           8/8   yes     6/6     0    0     0
LLaRD    3 ml1m         passed   8/8   yes     6/6     0    0     0
total: 933 of 954 done, 2 running, 0 failed, 0 conflicts; held: none
GPU: 100 %, 14543 MiB, 24564 MiB
rough finish: Sun 08 Nov 23:57 (8.6 h of known work)
---- RQ2 (after Part C) ----
  waits until Part C has nothing left to run
---- queue log (~/survey_queue.log) ----
  2026-11-08 13:05:12 [pc1-queue] waiting for Part C to finish (Part C running: 3; idle checks 0/3); next look in 10 min
  2026-11-08 13:15:12 [pc1-queue] waiting for Part C to finish (Part C running: 3; idle checks 0/3); next look in 10 min
  2026-11-08 13:25:12 [pc1-queue] waiting for Part C to finish (Part C running: 3; idle checks 0/3); next look in 10 min
  2026-11-08 13:35:12 [pc1-queue] waiting for Part C to finish (Part C running: 3; idle checks 0/3); next look in 10 min
  2026-11-08 13:45:12 [pc1-queue] waiting for Part C to finish (Part C running: 3; idle checks 0/3); next look in 10 min
  2026-11-08 13:55:12 [pc1-queue] waiting for Part C to finish (Part C running: 2; idle checks 0/3); next look in 10 min
  2026-11-08 14:05:13 [pc1-queue] waiting for Part C to finish (Part C running: 2; idle checks 0/3); next look in 10 min
  2026-11-08 14:15:13 [pc1-queue] waiting for Part C to finish (Part C running: 2; idle checks 0/3); next look in 10 min
  2026-11-08 14:25:13 [pc1-queue] waiting for Part C to finish (Part C running: 2; idle checks 0/3); next look in 10 min
  2026-11-08 14:35:13 [pc1-queue] waiting for Part C to finish (Part C running: 2; idle checks 0/3); next look in 10 min
  2026-11-08 14:45:13 [pc1-queue] waiting for Part C to finish (Part C running: 2; idle checks 0/3); next look in 10 min
  2026-11-08 14:55:13 [pc1-queue] waiting for Part C to finish (Part C running: 2; idle checks 0/3); next look in 10 min
  2026-11-08 15:05:13 [pc1-queue] waiting for Part C to finish (Part C running: 2; idle checks 0/3); next look in 10 min
  2026-11-08 15:15:13 [pc1-queue] waiting for Part C to finish (Part C running: 2; idle checks 0/3); next look in 10 min
  2026-11-08 15:25:13 [pc1-queue] waiting for Part C to finish (Part C running: 2; idle checks 0/3); next look in 10 min
---- recent service log lines ----
2026-11-08T14:55:16+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-08T15:05:13+00:00 home systemd[3714]: partc-resume.service: Failed to open /run/user/1000/systemd/transient/partc-resume.service: No such file or directory
2026-11-08T15:05:13+00:00 home systemd[3714]: partc-resume.service: Failed to open /run/user/1000/systemd/transient/partc-resume.service: No such file or directory
2026-11-08T15:15:13+00:00 home systemd[3714]: partc-resume.service: Failed to open /run/user/1000/systemd/transient/partc-resume.service: No such file or directory
2026-11-08T15:15:13+00:00 home systemd[3714]: partc-resume.service: Failed to open /run/user/1000/systemd/transient/partc-resume.service: No such file or directory
2026-11-08T15:25:13+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-08T15:25:13+00:00 home systemd[3714]: partc-resume.service: Failed to open /run/user/1000/systemd/transient/partc-resume.service: No such file or directory
2026-11-08T15:25:13+00:00 home systemd[3714]: partc-resume.service: Failed to open /run/user/1000/systemd/transient/partc-resume.service: No such file or directory
```
