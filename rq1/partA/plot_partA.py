"""RQ1 Part A figures from partA/papers_coding.csv (no GPU, no training).

  python partA/plot_partA.py --csv partA/papers_coding.csv --out figures

Writes:
  figures/partA_family_by_year.pdf   stacked bars: papers per treatment family per year
  figures/partA_dataset_reuse.pdf    how many papers use each dataset (top 20), one-off datasets counted
  figures/partA_stats.txt            the numbers behind both, plus code-release and evaluation-noise shares
Fill in the blank columns (noise_targeted, detection_signal, foundation) for all papers before the final run.
"""
import argparse
import collections
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

FAMILY = {"T1": "Reweighting & selection", "T2": "Label & negative correction", "T3": "Graph refinement",
          "T4": "Representation purification", "T5": "Sequence purification", "T6": "Generative reconstruction",
          "T7": "Robust objectives"}
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"]  # fixed order, never cycled


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="partA/papers_coding.csv")
    ap.add_argument("--out", default="figures")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    df = pd.read_csv(a.csv)
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})

    # Figure 1a: family by year
    tab = df.pivot_table(index="year", columns="family", values="paper", aggfunc="count", fill_value=0)
    tab = tab.reindex(columns=list(FAMILY), fill_value=0).sort_index()
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    bottom = None
    for col, color in zip(FAMILY, COLORS):
        ax.bar(tab.index.astype(str), tab[col], bottom=bottom, color=color, label=f"{col} {FAMILY[col]}",
               edgecolor="white", linewidth=1)
        bottom = tab[col] if bottom is None else bottom + tab[col]
    ax.set_ylabel("Papers")
    ax.set_title("Denoising papers per treatment family, 2021-2026", loc="left", fontsize=10)
    ax.legend(frameon=False, fontsize=7, bbox_to_anchor=(1.01, 1), loc="upper left")
    ax.grid(axis="y", color="#e5e4e0", linewidth=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(os.path.join(a.out, "partA_family_by_year.pdf"))

    # Figure 1b: dataset reuse
    cnt = collections.Counter()
    for s in df["datasets"].dropna():
        for d in set(x.strip() for x in s.split(";") if x.strip()):
            cnt[d] += 1
    top = cnt.most_common(20)
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.barh([d for d, _ in top][::-1], [c for _, c in top][::-1], color=COLORS[0], height=0.6)
    for i, (_, c) in enumerate(top[::-1]):
        ax.text(c + 0.1, i, str(c), va="center", fontsize=7, color="#52514e")
    ax.set_xlabel("Papers using the dataset")
    once = sum(1 for c in cnt.values() if c == 1)
    ax.set_title(f"Dataset reuse: {len(cnt)} datasets, {once} used by one paper only", loc="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(a.out, "partA_dataset_reuse.pdf"))

    with open(os.path.join(a.out, "partA_stats.txt"), "w") as f:
        f.write(tab.to_string() + "\n\n")
        f.write("venue tier:\n" + df["venue_tier"].value_counts().to_string() + "\n\n")
        f.write("evaluation noise:\n" + df["evaluation_noise"].value_counts().to_string() + "\n\n")
        has_code = df["code"].fillna("").str.startswith("github.com") & ~df["code"].fillna("").str.contains("placeholder")
        f.write(f"papers with a public code link: {has_code.sum()} of {len(df)}\n")
        f.write("code link share by year:\n" + has_code.groupby(df["year"]).mean().round(2).to_string() + "\n\n")
        f.write("top datasets:\n" + "\n".join(f"{c:3d}  {d}" for d, c in cnt.most_common(30)) + "\n")
    print(open(os.path.join(a.out, "partA_stats.txt")).read())


if __name__ == "__main__":
    main()
