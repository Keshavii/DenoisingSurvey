# Unattended running on PC1, PC2, PC3

| PC | What runs | How |
|---|---|---|
| PC1 aura3@home | RQ1 Part C (then RQ2, being built) | `partc.service` (unchanged) |
| PC2 anurag@home | RQ4 ML-1M: tuning, picks, all finals; then RQ4 Yelp finals of seed 2 | `survey-queue.service` → `pc2_queue.sh` |
| PC3 aura1@aura-node1 | RQ4 Yelp: tuning, picks, finals of seed 1 | `survey-queue.service` → `pc3_queue.sh` |

Every PC: `survey-snapshot.timer` pushes status and all small result files every 30 min to the branch
**status** — read it at https://github.com/Keshavii/DenoisingSurvey/tree/status (`pc1/STATUS.md`, `pc2/STATUS.md`,
`pc3/STATUS.md`; a line starting with `ALERT` needs a look).

All services start at boot (linger is on) and resume where they stopped: nothing to do after a reboot.

## Commands (on the PC itself)

    bash ~/survey/rq1/scripts/ops/status.sh          # one screen
    tail -20 ~/survey_queue.log                       # the queue's own log (PC2, PC3)
    bash ~/survey/rq1/scripts/ops/install.sh          # set up / repair (safe to run again; does not restart a running queue)
    systemctl --user stop survey-queue                # stop the queue (kills its running jobs; they rerun on start)
    systemctl --user restart survey-queue             # after a code change (git pull), same effect on running jobs

## RQ4 across two PCs

PC2 tunes and runs ML-1M (R4 and R5 need PC2's Llama files). PC3 tunes Yelp and publishes its picks
(`pc3/rq1/configs/rq4/picks_yelp.json` on the status branch); PC2 then runs Yelp seed 2 with those picks while PC3 runs
seed 1. Both use the same Yelp files (copied once from PC2, below), so a Yelp result does not depend on which PC ran it.
Each queue pass is followed by a pass that reruns failed jobs one at a time (a job that ran out of GPU memory next
to three others runs alone).

## Copy Yelp from PC2 to PC3 (once)

On PC2:

    cd ~/survey/rq1 && tar czf ~/yelp_for_pc3.tgz data/yelp runs/rq4_prep/yelp_mf_clean runs/_rq4_ref/yelp_*

Move `~/yelp_for_pc3.tgz` to PC3's home folder (scp, USB drive, ...), then on PC3:

    cd ~/survey/rq1 && tar xzf ~/yelp_for_pc3.tgz && ls data/yelp

PC3's queue notices the data within 10 minutes and starts.
