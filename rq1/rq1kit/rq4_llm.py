"""RQ4 signal R5 (reasoning-driven, knowledge-based foundation): Llama-3.1-8B-Instruct judges whether a training
interaction fits the user's history. ML-1M only (the other datasets carry no item text).

Which interactions are scored: the --cap share (default 20%, as in the design doc) of positives with the highest
BCE loss under the plain reference LightGCN-BCE of the same training file (rq1kit.rq4 --make_ref), so the LLM cost
stays fixed per dataset. Everything else stays unscored (never treated in RQ4).

Prompt: up to --hist (20) of the user's other training movies (seeded sample) and the candidate movie (title, year, genres
from the raw MovieLens files, as in rq1kit.llard_knowledge). One output token; the score is
P(No) / (P(Yes) + P(No)) from the token log-probabilities, the probability that the interaction does not fit.

  python -m rq1kit.rq4_llm --data data/ml1m --train_file train_N3_20_s1.tsv --ref runs/_rq4_ref/<folder> \
      --raw ~/rq1-data/ml-1m --model ~/models/Llama-3.1-8B-Instruct
Output: <data>/rq4_llm/<build>.npz with user, item, p_noise, loss (resumes from <build>.part.npz).
"""
import argparse
import os
import time

import numpy as np
import pandas as pd

SYSTEM = ("You check the interaction log of a movie recommender. Given the movies a user watched, decide whether a "
          "candidate movie fits this user's taste or looks like an accidental or uncharacteristic interaction. "
          "Answer with exactly one word: Yes if it fits, No if it does not.")


def build_name(train_file):
    b = os.path.splitext(os.path.basename(train_file))[0]
    return "N0" if b == "train" else b.replace("train_", "")


def select_edges(train, ref_U, ref_I, cap):
    """Positives with the highest BCE loss under the reference model; returns users, items, losses."""
    u, i = train["user"].values, train["item"].values
    x = (ref_U[u] * ref_I[i]).sum(1)
    loss = np.logaddexp(0, -x)
    n = int(round(cap * len(u)))
    top = np.argsort(-loss, kind="mergesort")[:n]
    return u[top], i[top], loss[top]


def prompts_for(users, items, hist, lines, n_hist, seed):
    out = []
    for u, i in zip(users, items):
        h = [j for j in hist[u] if j != i]
        if len(h) > n_hist:
            h = sorted(np.random.default_rng([seed, int(u), int(i)]).choice(h, n_hist, replace=False))
        watched = "\n".join(f"- {lines[j]}" for j in h) or "- (none)"
        out.append(f"Movies the user watched:\n{watched}\n\nCandidate movie: {lines[i]}\n\nDoes the candidate fit "
                   "this user's taste? Answer Yes or No.")
    return out


def p_no_from(top_logprobs, text):
    """P(No) / (P(Yes) + P(No)) from the first token's top log-probabilities {token: logprob}; the generated text is
    the fallback when neither word is among them."""
    py = sum(np.exp(lp) for t, lp in top_logprobs.items() if t.strip().lower() == "yes")
    pn = sum(np.exp(lp) for t, lp in top_logprobs.items() if t.strip().lower() == "no")
    if py + pn > 0:
        return float(pn / (py + pn))
    t = text.strip().lower()
    return 1.0 if t.startswith("no") else 0.0 if t.startswith("yes") else float("nan")


class VLLMJudge:
    def __init__(self, path):
        from vllm import LLM
        self.llm = LLM(model=os.path.expanduser(path), dtype="bfloat16", max_model_len=4096, gpu_memory_utilization=0.85, seed=0)

    def __call__(self, prompts):
        from vllm import SamplingParams
        convs = [[{"role": "system", "content": SYSTEM}, {"role": "user", "content": p}] for p in prompts]
        outs = self.llm.chat(convs, SamplingParams(temperature=0.0, max_tokens=1, logprobs=20, seed=0), use_tqdm=False)
        res = []
        for o in outs:
            lp = o.outputs[0].logprobs[0] if o.outputs[0].logprobs else {}
            res.append(p_no_from({v.decoded_token: v.logprob for v in lp.values()}, o.outputs[0].text))
        return res


class StubJudge:
    """Tests only: 'No' when the candidate's genres share nothing with the first watched movie."""
    def __call__(self, prompts):
        res = []
        for p in prompts:
            first = p.split("\n")[1]
            cand = p.split("Candidate movie: ")[1].split("\n")[0]
            g1 = set(first.split("genres: ")[-1].split(", ")) if "genres: " in first else set()
            g2 = set(cand.split("genres: ")[-1].split(", "))
            res.append(p_no_from({"No": np.log(0.9), "Yes": np.log(0.1)} if not (g1 & g2) else
                                 {"Yes": np.log(0.8), "No": np.log(0.2)}, ""))
        return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--train_file", default="train.tsv")
    ap.add_argument("--ref", required=True, help="reference model folder printed by rq1kit.rq4 --make_ref (holds emb.npz)")
    ap.add_argument("--raw", default="~/rq1-data/ml-1m", help="folder with ml-1m.inter and ml-1m.item")
    ap.add_argument("--model", default="~/models/Llama-3.1-8B-Instruct")
    ap.add_argument("--backend", choices=["vllm", "stub"], default="vllm")
    ap.add_argument("--cap", type=float, default=0.2)
    ap.add_argument("--hist", type=int, default=20)
    ap.add_argument("--chunk", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args(argv)
    from .llard_knowledge import item_line, load_items
    data, raw = os.path.expanduser(a.data), os.path.expanduser(a.raw)
    meta = pd.read_json(os.path.join(data, "meta.json"), typ="series")
    train = pd.read_csv(os.path.join(data, a.train_file), sep="\t").drop_duplicates(["user", "item"])
    e = np.load(os.path.join(os.path.expanduser(a.ref), "emb.npz"))
    users, items, losses = select_edges(train, e["U"], e["I"], a.cap)
    lines = [item_line(r) for r in load_items(raw, int(meta["n_items"]))]
    hist = {u: g["item"].values for u, g in train.groupby("user")}
    out_dir = os.path.join(data, "rq4_llm")
    os.makedirs(out_dir, exist_ok=True)
    build = build_name(a.train_file)
    final, part = os.path.join(out_dir, f"{build}.npz"), os.path.join(out_dir, f"{build}.part.npz")
    if os.path.isfile(final):
        print(f"{final} exists"); return
    scores = np.full(len(users), np.nan, dtype=np.float32)
    done = 0
    if os.path.isfile(part):
        z = np.load(part)
        if len(z["p_noise"]) == len(users) and (z["user"] == users).all():
            scores, done = z["p_noise"], int(z["done"])
    judge = StubJudge() if a.backend == "stub" else VLLMJudge(a.model)
    t0 = time.time()
    for s in range(done, len(users), a.chunk):
        sl = slice(s, min(s + a.chunk, len(users)))
        scores[sl] = judge(prompts_for(users[sl], items[sl], hist, lines, a.hist, a.seed))
        done = sl.stop
        np.savez(part, user=users, item=items, p_noise=scores, loss=losses, done=done)
        print(f"{build}: {done}/{len(users)} scored, {time.time() - t0:.0f}s", flush=True)
    np.savez(final, user=users, item=items, p_noise=scores, loss=losses)
    os.remove(part)
    print(f"wrote {final}: {len(users)} interactions, {int(np.isnan(scores).sum())} unparsed, "
          f"mean P(no) {np.nanmean(scores):.3f}")


if __name__ == "__main__":
    main()
