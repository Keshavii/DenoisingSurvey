# Project plan: read this first

Full plan of action, decisions log and "mistakes not to repeat": the doc "Denoising Survey: Plan of Action",
https://claude.ai/artifact/Uk8RBTbZPC2tkYrTdv34TY . Read it at the start of every session and after every compaction.

Source of truth for the research questions: the doc "Experimental Design: 10 Research Questions for the Denoising
Survey" (15 Oct 2026), https://claude.ai/artifact/Y6z9w3htpheGc8kKxusVjv . The September PDF ("Experiment Design for
Our Denoising Survey", Akshada and Hiya) is NOT the plan: its 10 experiments were merged into our 10 RQs (mapping
below). Never use the PDF's numbering (E1..E10) as RQ numbers.

## The 10 RQs

| RQ | Question | Depends on | Priority (doc) |
|---|---|---|---|
| RQ1 | How have noise definition and treatment changed 2021-2026, and how much reported progress holds under one protocol? Part A map, Part B reproduction, Part C 13 methods under one protocol | none (core grid) | Must |
| RQ2 | Can we trust evaluation: natural vs injected noise (N0 vs N1/N2/N3 at rho*), proxy labels (300 human annotations), clean vs noisy validation for model selection | RQ1 | Must |
| RQ3 | Do methods find the noisy interactions? Detection AUC / precision@k of per-interaction scores, mistakes on long tail, N4 false-negative recovery, calibration | RQ1, RQ2 (needs score logging) | Must |
| RQ4 | Signal or treatment? 5 signals (loss, two-model disagreement, representation, structure, LLM) x 4 treatments (drop, reweight, relabel, resample) on LightGCN, D1-D3 | none | Should |
| RQ5 | Which family wins under which data: density x noise grid on Yelp and Gowalla; noise curves 0-50% for all core methods | RQ1, RQ2 | Must |
| RQ6 | Add a denoiser or switch model: plug-ins on MF-BPR, LightGCN, XSimGCL vs standalone SGL/XSimGCL/DiffRec/RGCF | RQ1 | Must |
| RQ7 | Cost: logged cost of every run, scaling on MIND-Large, fixed GPU budgets | all | Must |
| RQ8 | Who gains, who loses: user activity, cold/warm/established users, head/mid/tail items, coverage, Gini, D4-clean harm | RQ1, RQ2, RQ6 | Must |
| RQ9 | Unknown noise rate, no tuning: sensitivity, wrong noise rate (tune 10%, test 30%/N0), defaults, transfer | RQ1 | Should |
| RQ10 | Specialists for sequential (SASRec), multimodal (FREEDOM), social (LightGCN-S) settings, 11 specialist methods | none | Should |

Benchmark and leaderboard: a deliverable section, not an RQ.

## September PDF experiment -> our RQ

E1 -> RQ1 Part A. E2 -> RQ2 (noisy vs clean validation) and RQ9 (wrong noise rate); its "evaluate one model at
different test-time noise ratios" does not apply to CF (test pairs carry no noise). E3 -> RQ2 proxy-label check.
E4 -> RQ5 noise curves (its method list not adopted). E5 -> RQ3 (calibration). E6 -> RQ1 Part B (all 13 core methods
instead of 5). E7, E8 -> RQ8. E9 -> RQ7. E10 -> benchmark deliverable.

## Machines

- PC1 (prompt aura3@home, kit ~/rq1-kit): RQ1, then every RQ that builds on RQ1 runs (RQ2, RQ3, RQ5, RQ6, RQ7, RQ8, RQ9).
- PC2 (prompt anurag@home, kit ~/survey/rq1): RQs independent of RQ1 (RQ4, RQ10, RQ7 scaling and budget runs). Do NOT run RQ1 jobs on PC2.
- Rule agreed 3 Nov 2026 (user). Llama-3.1-8B-Instruct and the vllm env live on PC2.
- PC3 (prompt aura1@aura-node1, kit ~/survey/rq1), added 3 Nov: RTX 4090 24 GB, i9-14900K, 62 GB RAM + 71 GB swap,
  261 GB free disk (1.2 TB is someone else's containerd images: do not touch). rq1 env identical to PC1 (py 3.10.22,
  torch 2.5.1+cu121, numpy 2.2.6, scipy 1.15.3, pandas 2.3.3); RGCF and RQ4 tests pass. Runs a foreign docker stack
  ("aura" app, qdrant, postgres, redis, monitoring) and a vLLM container (Qwen3-32B-AWQ) that is crash-looping on a
  missing model path; if its owner fixes it, it takes ~20 GB of GPU memory. Role pending the owner's answer; proposed RQ10.
- PC4 (prompt aura@aura4), added 3 Nov: RTX 5090 32 GB (Blackwell, driver 595.99), i9-14900K, 62 GB RAM + 79 GB swap,
  1.7 TB free; foreign monitoring containers only. USER RULE (3 Nov): every reported result comes from an RTX 4090.
  PC4 produces NO reported results (no GPU training of any kind). At most a staging box for CPU-only, seeded,
  machine-independent work (RQ10 data preparation, noise files, dry runs of job lists).
- Driver note (PC3, PC4): kernel 6.8.0-147 had no nvidia module; fix is
  `apt install linux-modules-nvidia-595-open-$(uname -r) linux-modules-nvidia-595-open-generic` (signed, Secure Boot stays on).

## Decisions in effect (Part C as run)

- 3 seeds, 8 tuning trials, conditions LightGCN N0, LightGCN N2_20, MF N0 (lean plan, not the doc's full 5 seeds / 20 trials).
- SGDL out of Part C (Adressa and Yelp exceed 24 GB). LLaRD on ML-1M only.
- RQ4, RQ9, RQ10 were set aside as future work earlier (minimum plan); with PC2 free, RQ4 and RQ10 are back on the table.
- Part B: authors' code unchanged, README versions; nearest working version on the 4090 is recorded.

## Known gaps

- RQ3 needs per-interaction scores logged during training; Part C does not log them yet.
- RQ2's clean vs noisy validation check can use history.jsonl (it logs both valid_clean and valid_noisy NDCG@20 each epoch).
- rq1kit/e2.py (test-time noise) answers a question the doc says does not apply to CF; keep only as a note.
- rq1kit/e78.py feeds RQ8; rq1kit/e2_shift.py is an N0 vs N2_20 ranking check, related to RQ2/RQ9 but not their design.

## RQ10 audit (4 Nov 2026, PC3)

Repos cloned and read at the commits in rq1/scripts/rq10_setup.sh. One conda env per code base at README versions;
the 4090 forces only the CUDA build of torch (full list of deviations in the script header).

| Method | Env | README versions | Home data in repo | Notes |
|---|---|---|---|---|
| FMLP-Rec | r10-fmlp | py3.7, torch 1.8 | Google Drive (8 datasets) | default eval uses 99 sampled negatives; full ranking needed |
| HSD, SSDRec | r10-recbole | torch 1.12.0, RecBole 1.0.1 | RecBole atomic files | dgl/pyg imported only in unused graph export |
| STEAM | r10-steam | torch 1.8.0+cu111 | Beauty, Sports, Yelp in repo | |
| IADSR | r10-iadsr | pip freeze, torch 2.5.1 | raw Amazon 2014 + notebook | SASRec/GRU4Rec/Caser scripts for Beauty only; LLM = Llama-3.1-8B-Instruct via llm2vec (paper); freeze pins conflict, installed --no-deps |
| PreferDiff | r10-preferdiff | none given | Beauty, Sports, Toys, CDs | hidden 3072, README shows 4-GPU runs: check 24 GB fit |
| DA-MRS | r10-damrs | py3.10.9, torch 2.0.0, pyg 2.3.0 | MMRec Baby/Sports/Clothing (Drive) | |
| GUIDER (+ FREEDOM) | r10-mmrec | py3.7.11, torch 1.11.0 (= MMRec) | MMRec (Drive) | |
| GDMSR | r10-gdmsr | torch 1.7.1 (+dgl) | ciao, douban, yelp in repo | |
| GBSR (+ LightGCN-S) | r10-gbsr | TF 1.15 (paper) / torch 1.10 port | douban_book, epinions, yelp in repo | TF 1.15 cannot use a 4090: authors' PyTorch port used, recorded as deviation |
| HDSR | r10-hdsr | torch 1.13.1+cu117, pyg 2.3.1 | Douban, Epinions, Yelp2018 in repo | repo opened: usable |

Social data: the design uses GBSR's release for all; GDMSR and HDSR get it converted to their input format
(data conversion only, no code change). Lean plan (design doc): 3 sequential, 2 multimodal, 2 social datasets, 3 seeds.
Open: common evaluation across code bases (each repo's own evaluator differs: sampled vs full ranking, splits).

### RQ10 social track: code facts (read 4 Nov) and decisions
- GBSR (torch port): seed fixed at 2023 in run_GBSR.py; selects the best epoch on testdata.npy (valdata = testdata in
  rec_dataset.py); saves the best checkpoint; num_user/num_item via CLI (hard-coded only for yelp/epinions names);
  has its own fake-tie files (attacked_user_users_<r>.npy, r in 0.2/0.5/1.0/2.0, ties added per user's tie count).
- GDMSR: selects on validation, saves the whole model (model.ckpt); evaluates against 100 sampled negatives.
- HDSR: seed fixed at 2024; dataset name and device ('cuda:1', fails on a one-GPU machine) are set in run_HDSR.py,
  which its README tells users to edit; selects on validation, saves a checkpoint.
Decisions (common protocol, no change to any training code):
- Each specialist trains on our files written in its own input format (variant data folders). Where a code base selects
  on "test" (GBSR), our validation split is given as its test file.
- Every method is scored by one evaluator (full ranking, Recall/NDCG@20, our test split) from its saved best
  checkpoint, loaded through a wrapper that imports the authors' classes unchanged.
- Seeds: where the code fixes the seed (GBSR, HDSR), the 3 repeats differ by noise draw only; recorded as a deviation.
- HDSR: only the README-sanctioned config lines (dataset, device) are set; recorded.
- Social noise levels follow the design (0, 25, 50% fake ties per user's real ties, GBSR's own procedure).

## Lessons (4 Nov)
- Every script that starts vLLM on PC2 must export VLLM_USE_FLASHINFER_SAMPLER=0 (no nvcc there). Missing it in
  rq4_run.sh stopped RQ4 at 03:31 on 4 Nov and left PC2 idle ~15 h.
- Long unattended pipelines must not let one optional step (R5 scoring) stop the rest.

## Unattended operation and decisions (5-6 Nov)
- All three PCs run systemd user service `survey-queue` (rq1/scripts/ops/pcN_queue.sh) and timer `survey-snapshot`
  (status + small result files to branch `status`, https://github.com/Keshavii/DenoisingSurvey/tree/status). PC3 has
  no GitHub login: PC2 relays its folder over SSH (~/.survey_relay). Details: rq1/scripts/ops/README.md.
- RQ4 split: PC2 = ML-1M (tune, picks, 831 finals) then Yelp seed 2; PC3 = Yelp tune + picks, RQ10 stage 1, Yelp seed 1.
  Yelp inputs (data/yelp incl. N3 files, MF, reference models) copied from PC2 to PC3, so both PCs use identical files.
  Every queue pass is followed by a pass that reruns failed jobs alone (11 ML-1M trials had run out of GPU memory).
- RQ2 lean (Claude, 5 Nov; user may overrule): Part C picks reused (no per-condition tuning), Adressa/Yelp/Amazon-Book/
  ML-1M, N1/N2/N3 at rho* (rate rho*/(1-rho*)), 3 seeds, LightGCN, all Part C methods with a pick except LLaRD, plus
  Plain-BPR/BCE. Starts on PC1 only when Part C has nothing left (scheduler.json slots_taken_by_legacy_queue = 4).
- RQ10 findings 5-6 Nov: FMLP noise files of 5 Nov inserted noise at any position and replaced 14.6% / 18.2% of test
  targets (results retired, .invalid); noise levels 20/30% did not follow the design (10/20% of training positions,
  STEAM protocol); STEAM's Yelp (16,552 items) is not the design's Yelp (FMLP's, 20,033); PreferDiff's code has no
  Beauty (C, O, T only), its Sports run is the 4 Nov reproduction; no common evaluator yet. Stage 1 fixes the
  reproduction runs (rq10_stage1.sh). Stage 2 (rq10_stage2.sh, run right after stage 1): seq_noise.py builds N0/I10/I20
  (insertion before training items with p 0.1/0.2, validation and test untouched, same noisy sequences in FMLP,
  STEAM and RecBole format, injected positions saved); scoring = full ranking, leave-one-out, Recall@10/NDCG@10 via
  FMLP --full_sort, RecBole full mode (HSD) and steam_full_eval.py (best validation epoch, corrected sequence;
  reproduces STEAM's own sampled numbers exactly); table results/stage2_summary.tsv. One noise draw (seed 1) for now.
