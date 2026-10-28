"""LLM knowledge for LLaRD on the kit's ML-1M (Part C): profiles, embeddings and denoising knowledge, rebuilt from the
KIT'S OWN training file, so nothing from validation or test reaches the model.

Why this exists: LLaRD (Wang et al., 2025) trains on four things per dataset that its repo ships only for its own
Yelp / Amazon-Book subsets and never for the kit's splits: user and item profile embeddings (`prf_k/usr_emb_np.pkl`,
`itm_emb_np.pkl`) and the denoising knowledge mined by an LLM (`rel_k/aug_traindata.npy`, `rel_k/uu_data.npy`).
The authors' repo has the three prompts but not the code that builds those files; the format was read from their code
and checked on their Yelp files: per user at most 1 item added, at most 1 item deleted and exactly 1 added user.

Pipeline, one build per training file (natural data, and each injected-noise seed):
  items   (shared by all builds, depends only on the movie text)
          1. item profile: Llama writes a short profile from title, year and genres            (own prompt)
          2. item attribute keywords from the profile                                          (LLaRD system_item_prompt)
  users   3. user profile: Llama summarises the user's training history                       (own prompt)
          4. step 1: user keywords and High/Medium/Low rating of each shown history item       (LLaRD step1_system_prompt)
  knowledge
          5. neighbours: 5 most similar users (cosine on the training graph); 10 candidate items from those users that
             the user has not interacted with (the "2-hop" and "3-hop" of the prompt)
          6. step 2-4: LLaRD system_prompt_cot picks item_B (drop), user_C (add user), item_D (add item)
          7. aug_traindata = history minus item_B plus item_D;  uu_data = [user_C]; invalid picks are dropped, not guessed
  embed   8. profile text -> sentence embedding (BAAI/bge-base-en-v1.5), row k = user / item k

Recorded adaptations (all go to the Progress Log): Llama-3.1-8B-Instruct instead of Qwen-long; the item and user
profile prompts are our own (not in the authors' repo); ML-1M text is only title, year and genres; at most `--cap` (50)
history items are shown to the LLM, drawn at random from the whole training history so injected noise is visible;
neighbour rules are ours (not in the authors' repo); local sentence embeddings instead of OpenAI's.

  python -m rq1kit.llard_knowledge --stage items --data data/ml1m --raw ~/repos/RGCF/dataset/ml-1m \
      --prompts ~/repos/LLaRD/system_prompt --out data/ml1m/llard --model ~/models/Llama-3.1-8B-Instruct
  python -m rq1kit.llard_knowledge --stage users|knowledge --train_file train.tsv --build N0 ...
  python -m rq1kit.llard_knowledge --stage embed --build N0 ...
"""
import argparse
import json
import os
import pickle
import re
import time

import numpy as np
import pandas as pd
import scipy.sparse as sp

ITEM_PROFILE_SYSTEM = (
    "You write a short profile of a movie for a recommender system: one paragraph of at most 80 words with its basic "
    "information and what types of users would enjoy it. Use the given information and general knowledge of the film; "
    "do not invent facts you are not sure of.")
USER_PROFILE_SYSTEM = (
    "You write a short profile of a user for a recommender system: one paragraph of at most 100 words summarising what "
    "types of items this user is likely to enjoy, from the list of movies the user interacted with.")


# ------------------------------------------------------------------------------------------------ backends
class VLLM:
    def __init__(self, path):
        from vllm import LLM
        self.llm = LLM(model=os.path.expanduser(path), dtype="bfloat16", max_model_len=8192, gpu_memory_utilization=0.85, seed=0)

    def chat(self, kind, system, users, max_tokens, temperature=0.0):
        from vllm import SamplingParams
        convs = [[{"role": "system", "content": system}, {"role": "user", "content": u}] for u in users]
        outs = self.llm.chat(convs, SamplingParams(temperature=temperature, max_tokens=max_tokens, seed=0), use_tqdm=False)
        return [o.outputs[0].text for o in outs]


class Stub:
    """Deterministic fake model for tests: valid answers built from the request, no GPU."""
    def chat(self, kind, system, users, max_tokens, temperature=0.0):
        out = []
        for u in users:
            if kind in ("item_profile", "user_profile"):
                out.append("A short profile. " + u[:60])
            elif kind == "item_attrs":
                d = json.loads(u)
                out.append(json.dumps({"Item_index": d["item_index"], "Attributes": ["kw%d" % (d["item_index"] % 3), "common"]}))
            elif kind == "step1":
                d = json.loads(u)
                hist = list(d["history"])
                out.append(json.dumps({"User_id": d["current_user"], "Keywords": ["k%d" % (d["current_user"] % 4)],
                                       "Ratings": {i: ("High" if n < 2 else "Low") for n, i in enumerate(hist)}}))
            elif kind == "cot":
                d = json.loads(u)
                b = list(d["rated_history"])[-1]
                c = list(d["2-hop"])[0] if d["2-hop"] else None
                i = list(d["3-hop"])[0] if d["3-hop"] else None
                if d["current_user"] % 5 == 0:  # an invalid answer now and then, to exercise the checks
                    c = 99999
                out.append(json.dumps({"User_id": d["current_user"], "Step2": "x", "Step3": "y",
                                       "Step4": {"item_B": int(b), "user_C": c, "item_D": i}}))
        return out


def parse_json(text):
    try:
        a, b = text.index("{"), text.rindex("}")
        return json.loads(text[a:b + 1])
    except (ValueError, json.JSONDecodeError):
        return None


def ask_json(backend, kind, system, prompts, max_tokens):
    """One answer per prompt, parsed; a failed parse is asked again once with some randomness, then left as None."""
    texts = backend.chat(kind, system, prompts, max_tokens)
    res = [parse_json(t) for t in texts]
    bad = [i for i, r in enumerate(res) if r is None]
    if bad:
        again = backend.chat(kind, system, [prompts[i] for i in bad], max_tokens, temperature=0.3)
        for i, t in zip(bad, again):
            res[i] = parse_json(t)
    return res, sum(r is None for r in res)


# ------------------------------------------------------------------------------------------------ data
def load_items(raw_dir, n_items):
    """Kit item k is the k-th smallest raw ML-1M movie id (scripts/prepare_data.py reindexes with sort=True)."""
    inter = pd.read_csv(os.path.join(raw_dir, "ml-1m.inter"), sep="\t")
    raw_ids = np.sort(inter[inter.columns[1]].unique())
    assert len(raw_ids) == n_items, f"{len(raw_ids)} rated movies, the kit has {n_items} items"
    try:
        it = pd.read_csv(os.path.join(raw_dir, "ml-1m.item"), sep="\t")
    except UnicodeDecodeError:
        it = pd.read_csv(os.path.join(raw_dir, "ml-1m.item"), sep="\t", encoding="latin-1")
    it.columns = [c.split(":")[0] for c in it.columns]
    it = it.set_index("item_id")
    rows = []
    for k, rid in enumerate(raw_ids):
        r = it.loc[rid]
        rows.append(dict(item=k, raw_id=int(rid), title=str(r["movie_title"]), year=str(r["release_year"]), genres=str(r["genre"])))
    return rows


def item_line(r):
    return f"{r['title']} ({r['year']}), genres: {r['genres'].replace(' ', ', ')}"


def read_prompts(d):
    d = os.path.expanduser(d)
    return {k: open(os.path.join(d, f)).read() for k, f in
            dict(step1="step1_system_prompt.txt", item="system_item_prompt.txt", cot="system_prompt_cot.txt").items()}


def read_train(data_dir, train_file):
    meta = json.load(open(os.path.join(data_dir, "meta.json")))
    tr = pd.read_csv(os.path.join(data_dir, train_file), sep="\t").drop_duplicates(["user", "item"])
    return meta, tr


def dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(obj, open(path, "w"))


# ------------------------------------------------------------------------------------------------ stages
def stage_items(a, backend):
    meta = json.load(open(os.path.join(a.data, "meta.json")))
    rows = load_items(a.raw, meta["n_items"])
    P = read_prompts(a.prompts)
    d = os.path.join(a.out, "items")
    texts = backend.chat("item_profile", ITEM_PROFILE_SYSTEM, [f"Movie: {item_line(r)}." for r in rows], 200)
    texts = [t.strip() for t in texts]
    res, nfail = ask_json(backend, "item_attrs", P["item"],
                          [json.dumps({"item_index": r["item"], "profile": t}) for r, t in zip(rows, texts)], 120)
    attrs = [list(map(str, (x or {}).get("Attributes") or r["genres"].split())) for x, r in zip(res, rows)]
    dump(os.path.join(d, "itm_prf.json"), texts)
    dump(os.path.join(d, "itm_attrs.json"), attrs)
    dump(os.path.join(d, "items.json"), rows)
    dump(os.path.join(d, "report.json"), dict(n_items=len(rows), attr_parse_failures=nfail))
    print(f"items: {len(rows)} profiles, {nfail} attribute answers unparsable (fallback: genres)")


def shown_history(tr, n_users, cap, seed):
    hist = {u: g["item"].values for u, g in tr.groupby("user")}
    shown = {}
    for u in range(n_users):
        h = hist.get(u, np.array([], dtype=int))
        if len(h) > cap:
            h = np.sort(np.random.default_rng([seed, u]).choice(h, cap, replace=False))
        shown[u] = [int(i) for i in h]
    return {u: [int(i) for i in v] for u, v in hist.items()}, shown


def stage_users(a, backend):
    meta, tr = read_train(a.data, a.train_file)
    n_users = meta["n_users"]
    P = read_prompts(a.prompts)
    items = json.load(open(os.path.join(a.out, "items", "items.json")))
    attrs = json.load(open(os.path.join(a.out, "items", "itm_attrs.json")))
    full, shown = shown_history(tr, n_users, a.cap, a.seed)
    d = os.path.join(a.out, a.build)
    users = list(range(n_users))
    prompts = ["Movies the user interacted with:\n" + "\n".join("- " + item_line(items[i]) for i in shown[u]) for u in users]
    prf = [t.strip() for t in backend.chat("user_profile", USER_PROFILE_SYSTEM, prompts, 260)]
    s1p = [json.dumps({"current_user": u, "summarization": prf[u], "history": {str(i): attrs[i] for i in shown[u]}}) for u in users]
    res, nfail = ask_json(backend, "step1", P["step1"], s1p, 1100)
    step1 = {}
    for u, r in enumerate(res):
        r = r or {}
        rat = {str(k): v for k, v in (r.get("Ratings") or {}).items() if v in ("High", "Medium", "Low") and int(k) in set(shown[u])}
        step1[u] = dict(Keywords=[str(x) for x in (r.get("Keywords") or [])][:5], Ratings=rat)
    dump(os.path.join(d, "usr_prf.json"), prf)
    dump(os.path.join(d, "step1.json"), step1)
    dump(os.path.join(d, "shown.json"), shown)
    dump(os.path.join(d, "report_users.json"), dict(n_users=n_users, step1_unparsable=nfail,
         step1_without_ratings=sum(1 for v in step1.values() if not v["Ratings"])))
    print(f"users: {n_users} profiles, {nfail} step-1 answers unparsable")


def neighbours(tr, n_users, n_items, k_users, k_items):
    m = sp.csr_matrix((np.ones(len(tr), dtype=np.float32), (tr["user"].values, tr["item"].values)), shape=(n_users, n_items))
    norm = np.sqrt(np.asarray(m.sum(1)).ravel()) + 1e-9
    sim = (m @ m.T).toarray() / np.outer(norm, norm)
    np.fill_diagonal(sim, -1)
    nb_u = np.argsort(-sim, axis=1, kind="stable")[:, :k_users]
    out = {}
    for u in range(n_users):
        have = set(m.indices[m.indptr[u]:m.indptr[u + 1]])
        score = {}
        for v in nb_u[u]:
            for i in m.indices[m.indptr[v]:m.indptr[v + 1]]:
                if i not in have:
                    score[int(i)] = score.get(int(i), 0.0) + float(sim[u, v])
        cand = sorted(score, key=lambda i: (-score[i], i))[:k_items]
        out[u] = ([int(v) for v in nb_u[u]], cand)
    return out


def stage_knowledge(a, backend):
    meta, tr = read_train(a.data, a.train_file)
    n_users, n_items = meta["n_users"], meta["n_items"]
    P = read_prompts(a.prompts)
    attrs = json.load(open(os.path.join(a.out, "items", "itm_attrs.json")))
    d = os.path.join(a.out, a.build)
    prf = json.load(open(os.path.join(d, "usr_prf.json")))
    step1 = {int(k): v for k, v in json.load(open(os.path.join(d, "step1.json"))).items()}
    shown = {int(k): v for k, v in json.load(open(os.path.join(d, "shown.json"))).items()}
    full, _ = shown_history(tr, n_users, a.cap, a.seed)
    nb = neighbours(tr, n_users, n_items, 5, 10)
    prompts = []
    for u in range(n_users):
        rated = {str(i): step1[u]["Ratings"].get(str(i), "Medium") for i in shown[u]}
        prompts.append(json.dumps({"current_user": u, "summarization": prf[u], "keywords": step1[u]["Keywords"], "rated_history": rated,
                                   "2-hop": {str(v): step1[v]["Keywords"] for v in nb[u][0]},
                                   "3-hop": {str(i): attrs[i] for i in nb[u][1]}}))
    res, nfail = ask_json(backend, "cot", P["cot"], prompts, 600)
    aug, uu, bad = {}, {}, dict(unparsable=nfail, item_B=0, user_C=0, item_D=0)
    for u in range(n_users):
        hist = list(full.get(u, []))
        r = (res[u] or {}).get("Step4") or {}
        b, c, i = r.get("item_B"), r.get("user_C"), r.get("item_D")
        b_ok = isinstance(b, (int, str)) and str(b).lstrip("-").isdigit() and int(b) in set(shown[u])
        c_ok = isinstance(c, (int, str)) and str(c).lstrip("-").isdigit() and int(c) in set(nb[u][0])
        i_ok = isinstance(i, (int, str)) and str(i).lstrip("-").isdigit() and int(i) in set(nb[u][1])
        bad["item_B"] += not b_ok
        bad["user_C"] += not c_ok
        bad["item_D"] += not i_ok
        new = [x for x in hist if not (b_ok and x == int(b))]
        if i_ok and int(i) not in set(new):
            new.append(int(i))
        aug[u] = new
        uu[u] = [int(c)] if c_ok else []
    os.makedirs(os.path.join(d, "rel_k"), exist_ok=True)
    np.save(os.path.join(d, "rel_k", "aug_traindata.npy"), np.array(aug, dtype=object), allow_pickle=True)
    np.save(os.path.join(d, "rel_k", "uu_data.npy"), np.array(uu, dtype=object), allow_pickle=True)
    np.save(os.path.join(d, "traindata.npy"), np.array({u: list(full.get(u, [])) for u in range(n_users)}, dtype=object), allow_pickle=True)
    add = [len(set(aug[u]) - set(full.get(u, []))) for u in range(n_users)]
    dele = [len(set(full.get(u, [])) - set(aug[u])) for u in range(n_users)]
    rep = dict(n_users=n_users, invalid_or_missing=bad, mean_added=float(np.mean(add)), mean_deleted=float(np.mean(dele)),
               mean_uu=float(np.mean([len(v) for v in uu.values()])), source_train_file=a.train_file)
    dump(os.path.join(d, "report_knowledge.json"), rep)
    print("knowledge:", json.dumps(rep))


def embed_texts(texts, how, model_name):
    if how == "hash":  # tests only: deterministic pseudo-embeddings, no download
        out = np.zeros((len(texts), 16), dtype=np.float32)
        for n, t in enumerate(texts):
            out[n] = np.random.default_rng(abs(hash(t)) % (2 ** 32)).standard_normal(16)
        return out
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name).encode(texts, batch_size=128, normalize_embeddings=True, show_progress_bar=False).astype(np.float32)


def stage_embed(a, backend=None):
    d = os.path.join(a.out, a.build)
    os.makedirs(os.path.join(d, "prf_k"), exist_ok=True)
    itm = json.load(open(os.path.join(a.out, "items", "itm_prf.json")))
    usr = json.load(open(os.path.join(d, "usr_prf.json")))
    for name, texts in (("itm_emb_np.pkl", itm), ("usr_emb_np.pkl", usr)):
        e = embed_texts(texts, a.embed, a.embed_model)
        pickle.dump(e, open(os.path.join(d, "prf_k", name), "wb"))
        print(f"embed: {name} {e.shape}")


STAGES = dict(items=stage_items, users=stage_users, knowledge=stage_knowledge, embed=stage_embed)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=list(STAGES))
    ap.add_argument("--data", required=True, help="kit dataset folder, e.g. data/ml1m")
    ap.add_argument("--raw", default="~/repos/RGCF/dataset/ml-1m", help="folder with the raw MovieLens ml-1m.inter / ml-1m.item")
    ap.add_argument("--prompts", default="~/repos/LLaRD/system_prompt")
    ap.add_argument("--out", required=True, help="output root, e.g. data/ml1m/llard")
    ap.add_argument("--build", default="N0", help="N0, N2_20_s1, ... (one folder per training file)")
    ap.add_argument("--train_file", default="train.tsv")
    ap.add_argument("--model", default="~/models/Llama-3.1-8B-Instruct")
    ap.add_argument("--backend", choices=["vllm", "stub"], default="vllm")
    ap.add_argument("--embed", choices=["st", "hash"], default="st")
    ap.add_argument("--embed_model", default="BAAI/bge-base-en-v1.5")
    ap.add_argument("--cap", type=int, default=50, help="history items shown to the LLM")
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args(argv)
    a.raw, a.data, a.out = os.path.expanduser(a.raw), os.path.expanduser(a.data), os.path.expanduser(a.out)
    backend = None
    if a.stage != "embed":
        backend = Stub() if a.backend == "stub" else VLLM(a.model)
    t0 = time.time()
    STAGES[a.stage](a, backend)
    print(f"stage {a.stage} done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
