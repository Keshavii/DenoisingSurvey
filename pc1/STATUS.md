# pc1 status

```
pc1 (aura3@home)  2026-11-25 19:53:34 UTC  up since 2026-09-30 13:27:10
code 2b25825f 21 Nov 18:28  linger yes  disk free 992G  ram used 11/62 GB swap 0 GB 
gpu 100 %, 6381 MiB, 24564 MiB, 62
---- services ----
  partc.service                active running
  rq5more.service              active running
  survey-kick.service          inactive dead
  survey-queue.service         inactive dead
  survey-snapshot.service      activating start
  last snapshot: 2026-11-25 19:22:37 push ok (118e0cca; pc1)
---- gpu jobs ----
  29:07       bash -c python -m rq1kit.drrl --loss sl --lr_mult 10 --ssm_temp 0.12 --data data/ml1m --train_file train_RQ5N2_10_s1.ts
  29:07       python -m rq1kit.drrl --loss sl --lr_mult 10 --ssm_temp 0.12 --data data/ml1m --train_file train_RQ5N2_10_s1.tsv --mode
  20:32       bash -c python -m rq1kit.adt --method tce --drop_rate 0.05 --num_gradual 30000 --data data/ml1m --train_file train_RQ5N
  20:32       python -m rq1kit.adt --method tce --drop_rate 0.05 --num_gradual 30000 --data data/ml1m --train_file train_RQ5N2_10_s1.
  19:24       bash -c python -m rq1kit.bod --lr_mult 1 --generator_lr 0.01 --weight_uniformity 0.5 --data data/ml1m --train_file trai
  19:24       python -m rq1kit.bod --lr_mult 1 --generator_lr 0.01 --weight_uniformity 0.5 --data data/ml1m --train_file train_RQ5N2_
  03:44       bash -c python -m rq1kit.ddrm --diff_lr 0.0001 --alpha 0.5 --steps 10 --data data/ml1m --train_file train_RQ5N2_10_s1.t
  03:44       python -m rq1kit.ddrm --diff_lr 0.0001 --alpha 0.5 --steps 10 --data data/ml1m --train_file train_RQ5N2_10_s1.tsv --mod
  03:43       /home/aura3/miniconda3/envs/rq1/bin/python -m rq1kit.backbone --data data/ml1m --train_file train_RQ5N2_10_s1.tsv --mod
  18-01:48:17 python -u -m rq1kit.partc run --skip dcf,pld,sl
---- RQ1 Part C (partc driver status, refreshed every minute) ----
  status file written 2026-11-25 19:53:00
Part C status 2026-11-25 19:53  kit 2b25825f
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
GPU: 100 %, 6381 MiB, 24564 MiB   rq1kit.queue running (pids 52508 52727): partc shares the GPU, leaving it 4 slots
rough finish: Wed 25 Nov 19:53 (0.0 h of known work)
---- RQ2 (after Part C) ----
  started 2026-11-09 00:15:19
  rho*: adressa 0.607, ml1m 0.155, yelp 0.156, amazon_book 0.073
  rq2 adressa: 126/126 done, 0 failed so far
  rq2 amazon_book: 126/126 done, 0 failed so far
  rq2 ml1m: 126/126 done, 0 failed so far
  rq2 yelp: 126/126 done, 0 failed so far
---- RQ5 (noise curves, Yelp and Gowalla) ----
  rq5 gowalla: 126/126 done, 0 failed so far
  rq5 yelp: 126/126 done, 0 failed so far
---- queue log (~/survey_queue.log) ----
  2026-11-25 18:44:34 [pc1-queue] RQ2 1/4 rho*
  2026-11-25 18:44:34 [pc1-queue] RQ2 2/4 MF-BPR on the clean bases (top-K for N3)
  2026-11-25 18:44:34 [pc1-queue] RQ2 3/4 noise files
  2026-11-25 18:44:35 [pc1-queue] RQ2 4/4 runs
  504 RQ2 jobs
  0 jobs to run, 504 already done
  2026-11-25 18:44:35 [pc1-queue]   retry pass: failed RQ2 jobs, one at a time
  0 jobs to run, 504 already done
  2026-11-25 18:44:35 [pc1-queue] RQ5 1/2 noise files
  2026-11-25 18:44:35 [pc1-queue] RQ5 2/2 runs
  252 RQ5 jobs
  0 jobs to run, 252 already done
  2026-11-25 18:44:35 [pc1-queue]   retry pass: failed RQ5 jobs, one at a time
  0 jobs to run, 252 already done
  2026-11-25 18:44:35 [pc1-queue] PC1 queue complete: RQ2 and RQ5 finished (results/RQ2, results/RQ5)
---- recent service log lines ----
2026-11-25T18:44:33+00:00 home systemd[3714]: Started survey-queue.service - Survey unattended queue (pc1).
2026-11-25T18:44:33+00:00 home systemd[3714]: Finished survey-kick.service - Start survey-queue if it is not running.
2026-11-25T18:44:35+00:00 home systemd[3714]: survey-queue.service: Consumed 2.817s CPU time.
2026-11-25T18:51:33+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-25T18:51:37+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-25T19:22:33+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
2026-11-25T19:22:37+00:00 home systemd[3714]: Finished survey-snapshot.service - Survey status and results to GitHub (branch status).
2026-11-25T19:53:33+00:00 home systemd[3714]: Starting survey-snapshot.service - Survey status and results to GitHub (branch status)...
```
