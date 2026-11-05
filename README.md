# Live status of the survey PCs

Written automatically every 30 minutes by each PC (`rq1/scripts/ops/snapshot.sh` on branch main). Do not edit by hand.

- [pc1/STATUS.md](pc1/STATUS.md): PC1 aura3@home, RQ1 Part C
- [pc2/STATUS.md](pc2/STATUS.md): PC2 anurag@home, RQ4 ML-1M (+ Yelp seed 2)
- [pc3/STATUS.md](pc3/STATUS.md): PC3 aura1@aura-node1, RQ4 Yelp (+ RQ10)

Each folder also holds that PC's result files (`rq1/results/...`), the run.json and history.jsonl of every run, queue
state files, picks and logs. A line starting with `ALERT` in a STATUS.md needs a look. The time on the first line of a
STATUS.md tells you when that PC last reported; if it is more than an hour old, the PC is off, asleep or offline.
