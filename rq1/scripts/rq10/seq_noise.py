"""RQ10 sequential track, stage 2: noise as the design states it, one set of noisy sequences per dataset, written in
each code base's input format.

Design doc, RQ10 sequential track: "random items inserted into 10% and 20% of training sequence positions (STEAM's
protocol)"; data = the versions used by FMLP-Rec, HSD and SSDRec (FMLP's files); leave-one-out (last item = test,
second last = validation). Here:
  * canonical data: FMLP's <DS>.txt (user item item ...) and <DS>_sample.txt (99 negatives per user)
  * levels: N0 (as collected), I10, I20: before each training item (every item except the last two) one random item is
    inserted with probability 0.10 / 0.20; the random item is drawn uniformly from the items the user never touched.
    Validation and test items are never changed. The injected positions are written to <name>_noise.tsv.
  * formats:
      FMLP   <fmlp_data>/<DS>_<LV>_s<seed>.txt          full sequences (FMLP's own rule: uses the last 50 as input)
      STEAM  <steam_root>/<DS>_<LV>_s<seed>/{train,valid,test,valid_neg,test_neg}.dat
             STEAM's own preprocessing keeps the latest 50 items of each user: the same noisy sequence, from the clean
             item 50th from the end, cut to its last 60 items (STEAM's default -mml);
             negatives = FMLP's 99 sampled negatives (STEAM's own validation only; RQ10 scores by full ranking)
      RecBole (HSD, SSDRec) <recbole_root>/<DS>_<LV>_s<seed>/<DS>_<LV>_s<seed>.inter  (user_id, item_id, timestamp =
             position, so RecBole's TO order reproduces the sequence)
  * the STEAM item count for -n is max item id + 3 (written to <name>.meta.json)

  python seq_noise.py --fmlp_data DIR --datasets Beauty Sports_and_Outdoors Yelp --levels N0 I10 I20 --seeds 1 \
      --steam_root DIR --recbole_root DIR
"""
import argparse
import json
import os
import random

LEVELS = {"N0": 0.0, "I10": 0.10, "I20": 0.20}
STEAM_KEEP, STEAM_MAX = 50, 60


def read_fmlp(path):
    out = {}
    with open(path) as f:
        for line in f:
            p = line.split()
            if len(p) >= 2:
                out[int(p[0])] = [int(x) for x in p[1:]]
    return out


def noisy_sequences(seqs, p, seed, n_items):
    """Insert before each training item with probability p.
    Returns (sequences, noise rows (user, position, item), where[u] = position of each clean item in the noisy one)."""
    rng = random.Random(seed)
    out, rows, where = {}, [], {}
    for u in sorted(seqs):
        s = seqs[u]
        if p == 0 or len(s) < 3:
            out[u], where[u] = list(s), list(range(len(s)))
            continue
        seen = set(s)
        new, pos = [], []
        for it in s[:-2]:
            if rng.random() < p:
                r = rng.randint(1, n_items)
                while r in seen:
                    r = rng.randint(1, n_items)
                rows.append((u, len(new), r))
                new.append(r)
            pos.append(len(new))
            new.append(it)
        pos += [len(new), len(new) + 1]
        out[u], where[u] = new + s[-2:], pos
    return out, rows, where


def write_fmlp(seqs, path):
    with open(path + ".tmp", "w") as f:
        for u in sorted(seqs):
            f.write(f"{u} " + " ".join(map(str, seqs[u])) + "\n")
    os.replace(path + ".tmp", path)


def write_steam(clean, noisy, where, samples, folder):
    """STEAM files: the same noisy sequence as for FMLP, starting at the clean item that is 50th from the end
    (STEAM keeps a user's latest 50 items), then cut to its last 60 items (STEAM's -mml); user = line number."""
    os.makedirs(folder, exist_ok=True)
    users = sorted(clean)
    noisy = {u: noisy[u][where[u][max(0, len(clean[u]) - STEAM_KEEP)]:] for u in users}
    files = {k: open(os.path.join(folder, k + ".dat.tmp"), "w") for k in ("train", "valid", "test", "valid_neg", "test_neg")}
    longest = 0
    for u in users:
        s = noisy[u][-STEAM_MAX:]
        longest = max(longest, len(s))
        files["train"].write(",".join(map(str, s[:-2])) + "\n")
        files["valid"].write(",".join(map(str, s[:-1])) + "\n")
        files["test"].write(",".join(map(str, s)) + "\n")
        neg = ",".join(map(str, samples[u])) + "\n"
        files["valid_neg"].write(neg)
        files["test_neg"].write(neg)
    for k, f in files.items():
        f.close()
        os.replace(os.path.join(folder, k + ".dat.tmp"), os.path.join(folder, k + ".dat"))
    return longest


def write_recbole(seqs, folder, name):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name + ".inter")
    with open(path + ".tmp", "w") as f:
        f.write("user_id:token\titem_id:token\ttimestamp:float\n")
        for u in sorted(seqs):
            for t, it in enumerate(seqs[u]):
                f.write(f"{u}\t{it}\t{t}\n")
    os.replace(path + ".tmp", path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fmlp_data", required=True)
    ap.add_argument("--datasets", nargs="+", required=True)
    ap.add_argument("--levels", nargs="+", default=["N0", "I10", "I20"])
    ap.add_argument("--seeds", nargs="+", type=int, default=[1])
    ap.add_argument("--steam_root")
    ap.add_argument("--recbole_root")
    a = ap.parse_args()
    for ds in a.datasets:
        src = os.path.join(a.fmlp_data, ds + ".txt")
        smp = os.path.join(a.fmlp_data, ds + "_sample.txt")
        if not (os.path.isfile(src) and os.path.isfile(smp)):
            print(f"[skip] {ds}: {src} or {smp} missing")
            continue
        clean = read_fmlp(src)
        samples = read_fmlp(smp)
        n_items = max(max(max(s) for s in clean.values()), max(max(s) for s in samples.values()))
        assert set(samples) >= set(clean), f"{ds}: users without negatives"
        for lv in a.levels:
            for seed in a.seeds:
                name = f"{ds}_{lv}_s{seed}"
                p = LEVELS[lv]
                noisy, rows, where = noisy_sequences(clean, p, seed, n_items)
                train_pos = sum(max(0, len(s) - 2) for s in clean.values())
                write_fmlp(noisy, os.path.join(a.fmlp_data, name + ".txt"))
                with open(os.path.join(a.fmlp_data, name + "_noise.tsv"), "w") as f:
                    f.write("user\tposition\titem\n")
                    f.writelines(f"{u}\t{pos}\t{it}\n" for u, pos, it in rows)
                meta = {"dataset": ds, "level": lv, "p": p, "seed": seed, "users": len(clean), "n_items": n_items,
                        "steam_n": n_items + 3, "train_positions": train_pos, "inserted": len(rows),
                        "inserted_share_of_train_positions": len(rows) / max(1, train_pos)}
                if a.steam_root:
                    meta["steam_longest_test_seq"] = write_steam(clean, noisy, where, samples, os.path.join(a.steam_root, name))
                if a.recbole_root:
                    write_recbole(noisy, os.path.join(a.recbole_root, name), name)
                json.dump(meta, open(os.path.join(a.fmlp_data, name + ".meta.json"), "w"), indent=1)
                print(json.dumps(meta))


if __name__ == "__main__":
    main()
