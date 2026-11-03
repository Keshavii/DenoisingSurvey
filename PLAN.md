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
