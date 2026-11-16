#!/bin/bash
# RQ10 stage 2 for one more noise seed (the design wants 3 draws; stages 1-3 made seed 1 on PC3).
#   bash rq10_seed_run.sh <seed> [peer user@host]      log: ~/rq10_seeds.log (the queue appends to it)
# Sequential specialists FMLP-Rec, HSD, STEAM x {Beauty, Sports_and_Outdoors, Yelp} x {N0, I10, I20}: 27 runs, about 30 h
# (STEAM is 90% of it), one job at a time alone on the GPU, resumable (.done markers).
# On a PC that has no RQ10 yet (PC2, 16 Nov 2026) this first builds the three envs it needs (fmlp, steam, recbole:
# rq10_setup.sh with ENVS) and takes the authors' FMLP files for Sports_and_Outdoors and Yelp from the PC that has them
# (the peer, over SSH, same key as the status relay). The seed's noise is a function of (dataset, level, seed) only
# (seq_noise.py: random.Random(seed)); each seed is run on one PC only (seed 2 PC2, seed 3 PC3), so no result depends on
# two PCs drawing the same noise.
# Without the authors' Sports file stage 2 would silently use STEAM's copy; this script stops instead.
set -u
SEED=${1:?usage: rq10_seed_run.sh <seed> [peer user@host]}
PEER=${2:-${RQ10_PEER:-}}
ROOT=${ROOT:-$HOME/survey/rq10}
KIT=${KIT:-$HOME/survey/rq1}
F=$ROOT/repos/fmlp/data
say() { echo "$(date '+%F %T') [rq10-seed$SEED] $*"; }

need_env=""
for e in fmlp steam recbole; do [ -f "$ROOT/envs_ok/$e" ] || need_env="$need_env $e"; done
if [ -n "$need_env" ]; then
  say "building envs [$need_env ] (rq10_setup.sh, ENVS filter); this takes 20-60 min"
  ENVS="fmlp steam recbole" bash "$KIT/scripts/rq10_setup.sh" > "$HOME/rq10_setup.log" 2>&1
  for e in fmlp steam recbole; do
    [ -f "$ROOT/envs_ok/$e" ] || { say "env $e did not build (see ~/rq10_setup.log: $(grep -E 'FAILED' "$HOME/rq10_setup.log" | tail -2 | tr '\n' ' '))"; exit 1; }
  done
  ENVS="fmlp steam recbole" bash "$KIT/scripts/rq10_setup.sh" check 2>&1 | sed "s/^/  /"
fi

for f in Sports_and_Outdoors.txt Sports_and_Outdoors_sample.txt Yelp.txt Yelp_sample.txt; do
  [ -s "$F/$f" ] && continue
  [ -n "$PEER" ] || { say "$F/$f is missing and no peer is given (usage: rq10_seed_run.sh $SEED aura1@HOST)"; exit 1; }
  say "$f: from $PEER"
  scp -q -o BatchMode=yes -o ConnectTimeout=20 "$PEER:survey/rq10/repos/fmlp/data/$f" "$F/$f.tmp" && mv "$F/$f.tmp" "$F/$f" \
    || { say "$f: copy from $PEER failed"; rm -f "$F/$f.tmp"; exit 1; }
done
# a copy of PC3's file marked as STEAM's fallback would be the wrong data
[ -f "$F/Sports_and_Outdoors.SOURCE" ] && { say "Sports_and_Outdoors.SOURCE exists: this is the fallback copy, not the authors' file; stopping"; exit 1; }
for f in Sports_and_Outdoors Yelp Beauty; do
  [ "$(wc -l < "$F/$f.txt")" -gt 1000 ] || { say "$f.txt looks wrong ($(wc -l < "$F/$f.txt") lines)"; exit 1; }
done

say "stage 2, seed $SEED"
SEEDS=$SEED bash "$KIT/scripts/rq10/rq10_stage2.sh"
rc=$?
say "stage 2 seed $SEED finished with exit $rc"
exit $rc
