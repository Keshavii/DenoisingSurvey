# Denoising implicit feedback: experimental survey

Code, configurations, launch scripts and result files for an experimental survey of denoising methods for
implicit-feedback recommendation. Every number in the survey can be traced to a file in this repository.

## Layout

| Folder | What it holds |
|---|---|
| `rq1/` | RQ1: the paper map (Part A), reproductions of the original papers with their own code (Part B), and all methods under one protocol (Part C) |
| `rq1/rq1kit/` | The shared kit: data splits, backbones, method adapters, evaluator, job queue. Later RQs reuse it |
| `rq1/configs/` | Job lists, tuned settings (`best_plain.json`), repository commits used in Part B |
| `rq1/partB/pc1/`, `rq1/partB/pc2/` | The exact launch scripts used for each Part B reproduction, per machine |
| `rq1/results/` | Result files: Part B logs, Part C evaluator outputs (`results/C/<dataset>/<run>.json`) |
| `rq1/tables/`, `rq1/figures/` | Tables and figures built from `results/` |
| `rq2/` ... | Added as each research question starts |

## Not in the repository

Datasets (`data/`), training runs and checkpoints (`runs/`, `*.pt`, `*.npy`), job logs (`logs/`) and model
weights (`models/`) stay on the machines. `rq1/scripts/prepare_data.py` rebuilds the data splits.

## Machines

Two workstations, each with one NVIDIA RTX 4090 (24 GB), 62 GB RAM and 135 GB swap. Long jobs run as systemd user
services so they survive logouts. Part C runs on PC 1; PC 2 runs work that does not depend on Part C.

## Working rules

- Part B uses each paper's own code without changes to its method; compatibility fixes are recorded and classified.
- Each Part B repository runs on the versions its README names; where those cannot run on the RTX 4090, the
  nearest working version is used and recorded.
- Part C settings, grids and seeds are fixed in config files before a run starts; every run records the kit's git
  commit and its settings.
