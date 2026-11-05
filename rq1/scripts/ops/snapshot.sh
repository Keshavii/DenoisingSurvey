#!/bin/bash
# Publishes this PC's status and every small result file to the GitHub branch "status" (folder pc1/, pc2/ or pc3/), so
# progress can be read from anywhere: https://github.com/Keshavii/DenoisingSurvey/tree/status
# Run every 30 min by the systemd user timer survey-snapshot (install: scripts/ops/install.sh). Read-only towards the
# experiments: it never touches ~/survey's own checkout (main) and never starts or stops a job.
# Copied: result JSON/TSV/CSV, run.json and history.jsonl of every run, queue state files, picks, job lists, RQ10
# results and logs; nothing bigger than 20 MB and no model or array files (.pt .npy .npz .pkl).
set -u
REPO=${REPO:-$HOME/survey}
WT=${WT:-$HOME/survey-status}
LOG=${LOG:-$HOME/survey_snapshot.log}
case "$(whoami)" in aura3) PC=pc1 ;; anurag) PC=pc2 ;; aura1) PC=pc3 ;; *) PC=${PC:-$(whoami)} ;; esac
KIT=$REPO/rq1; [ "$PC" = pc1 ] && [ -d "$HOME/rq1-kit" ] && KIT=$HOME/rq1-kit
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
exec 9> "$HOME/.survey_snapshot.lock"
flock -n 9 || { say "previous snapshot still running; skipped"; exit 0; }
export GIT_AUTHOR_NAME="$PC snapshot" GIT_AUTHOR_EMAIL="$PC@denoising-survey.invalid"
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME" GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"

if [ ! -e "$WT/.git" ]; then
  git -C "$REPO" fetch -q origin status 2>> "$LOG" || { say "push FAILED: cannot fetch branch status"; exit 1; }
  git -C "$REPO" worktree prune
  git -C "$REPO" worktree add -q --detach "$WT" origin/status 2>> "$LOG" || { say "push FAILED: cannot create $WT"; exit 1; }
fi
cd "$WT" || exit 1
git fetch -q origin status 2>> "$LOG" && git reset -q --hard origin/status

mkdir -p "$PC"
{
  echo "# $PC status"
  echo
  echo '```'
  bash "$REPO/rq1/scripts/ops/status.sh" --full 2>&1
  echo '```'
} > "$PC/STATUS.md"

python3 - "$PC" "$KIT" "$HOME" "$WT/$PC" <<'EOF'
import fnmatch, os, shutil, sys
pc, kit, home, dest = sys.argv[1:5]
MAX = 20 * 2**20
SKIP = (".pt", ".pth", ".npy", ".npz", ".pkl", ".ckpt", ".bin", ".safetensors", ".lock")
# (source folder, patterns relative to it, destination folder)
specs = [(kit, ["results/**", "configs/rq4/*.json", "configs/rq4/*.csv", "configs/partc/best/*.json",
                "logs/*/state.jsonl", "logs/partc/status.txt", "logs/partc/driver.log", "tables/**",
                "runs/**/run.json", "runs/**/history.jsonl"], "rq1")]
if pc == "pc3":
    specs.append((os.path.join(home, "survey/rq10"), ["results/**", "logs/*.log", "logs/*.done", "logs/*.gpu"], "rq10"))
n = 0
# top-level experiment logs in the home folder (not recursive)
import glob
for p in sorted(set(sum((glob.glob(os.path.join(home, g)) for g in
                        ("rq4*.log", "rq10*.log", "survey_*.log", "partc*.log", "llard*.log", "pc*_queue.log")), []))):
    if os.path.isfile(p) and os.path.getsize(p) <= MAX:
        q = os.path.join(dest, "home_logs", os.path.basename(p))
        if not (os.path.exists(q) and os.path.getsize(q) == os.path.getsize(p) and int(os.path.getmtime(q)) == int(os.path.getmtime(p))):
            os.makedirs(os.path.dirname(q), exist_ok=True)
            shutil.copy2(p, q)
            n += 1
for src, pats, sub in specs:
    if not os.path.isdir(src):
        continue
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("survey-status", "survey", "miniconda3", "repos", "data", "models")]
        for f in files:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, src)
            if not any(fnmatch.fnmatch(rel, pat) for pat in pats) or f.endswith(SKIP) or os.path.islink(p):
                continue
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_size > MAX:
                continue
            q = os.path.join(dest, sub, rel)
            if os.path.exists(q) and os.path.getsize(q) == st.st_size and int(os.path.getmtime(q)) == int(st.st_mtime):
                continue
            os.makedirs(os.path.dirname(q), exist_ok=True)
            shutil.copy2(p, q)
            n += 1
print(n)
EOF

git add -A "$PC"
if git diff --cached --quiet; then say "nothing new"; exit 0; fi
git commit -q -m "$PC snapshot $(date '+%F %H:%M %Z')"
for i in 1 2 3; do
  if git push -q origin HEAD:status 2>> "$LOG"; then say "push ok ($(git log -1 --format=%h))"; exit 0; fi
  git fetch -q origin status 2>> "$LOG" && git rebase -q origin/status 2>> "$LOG" || git rebase --abort 2>/dev/null
  sleep $((i * 20))
done
say "push FAILED after 3 tries (credentials? network?)"
exit 1
