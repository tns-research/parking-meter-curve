"""Figures and tables for the paper. python3 analysis/paper_figures.py

Writes figures/fig_curves.pdf, figures/fig_tipping.pdf and
figures/numbers.json (cell counts, d50 per condition with bootstrap CI, median
response length)."""

import json
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from plot_sweep import wilson
from sweep import curve, d50, load

FILES = ["runs/sweep_s0s2.jsonl", "runs/sweep_placebo.jsonl", "runs/sweep_s4s5.jsonl", "runs/sweep_s1s3.jsonl"]
ORDER = ["S0", "PLACEBO", "S1", "S2", "S3", "S4", "S5"]
LABEL = {"S0": "No scaffold", "PLACEBO": "Placebo", "S1": "S1 constraints first", "S2": "S2 means-end",
         "S3": "S3 proxy check", "S4": "S4 simulation", "S5": "S5 causal system"}
GREY, BLUE, ORANGE, INK, MUTED, GRID = "#6b6a66", "#2a78d6", "#e8692e", "#0b0b0b", "#52514e", "#e6e5e0"


def boot_d50(df, s, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    cells = {d: g["walk"].to_numpy() for d, g in df[df.scaffold == s].groupby("distance_m")}
    out = [d50(pd.Series({d: rng.choice(v, len(v)).mean() for d, v in cells.items()}).sort_index()) for _ in range(n)]
    out = np.array(out)
    return np.percentile(out[np.isfinite(out)], [2.5, 97.5])


def style(ax):
    ax.set_ylim(-3, 103)
    ax.set_xlim(0, 520)
    ax.set_yticks([0, 50, 100])
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.axhline(50, color="#a8a79f", lw=0.8, ls=(0, (4, 3)))
    ax.tick_params(colors=MUTED, length=0, labelsize=8)
    for sp in ax.spines.values():
        sp.set_visible(False)


def main():
    raw = pd.concat([load(f) for f in FILES], ignore_index=True)
    df = raw[raw.format_ok].copy()
    df["walk"] = (df.answer == "WALK").astype(int)
    c = curve(df)
    tab = df.groupby(["scaffold", "distance_m"]).walk.agg(["sum", "count"])
    tip = {s: d50(c.loc[s]["mean"]) for s in ORDER}
    ci = {s: boot_d50(df, s) for s in ORDER}

    fig, axes = plt.subplots(2, 3, figsize=(7.2, 4.4), sharex=True, sharey=True)
    for ax, s in zip(axes.flat, ORDER[1:]):
        style(ax)
        series = [("S0", GREY, "o", "-")] + ([("PLACEBO", BLUE, "s", "--")] if s != "PLACEBO" else []) + \
                 [(s, ORANGE if s != "PLACEBO" else BLUE, "^" if s != "PLACEBO" else "s", "-")]
        for name, col, mk, ls in series:
            t = tab.loc[name]
            if name == s or name == "S0":
                lo, hi = wilson(t["sum"].values, t["count"].values)
                ax.fill_between(t.index, 100 * lo, 100 * hi, color=col, alpha=0.13, lw=0)
            ax.plot(t.index, 100 * t["sum"] / t["count"], color=col, lw=1.6, ls=ls, marker=mk, ms=3.5)
        ax.set_title(f"{LABEL[s]}: {tip[s]:.0f} m", fontsize=9, color=INK, loc="left")
    for ax in axes[1]:
        ax.set_xlabel("Distance to the meter machine (m)", fontsize=8, color=MUTED)
    for ax in axes[:, 0]:
        ax.set_ylabel("WALK (%)", fontsize=8, color=MUTED)
    fig.tight_layout()
    fig.savefig("figures/fig_curves.pdf")

    fig, ax = plt.subplots(figsize=(5.2, 2.6))
    for i, s in enumerate(ORDER):
        col = GREY if s == "S0" else BLUE if s == "PLACEBO" else ORANGE
        ax.errorbar(tip[s], i, xerr=[[tip[s] - ci[s][0]], [ci[s][1] - tip[s]]], fmt="o", color=col, capsize=2, ms=5)
    ax.set_yticks(range(len(ORDER)))
    ax.set_yticklabels([LABEL[s] for s in ORDER], fontsize=8)
    ax.invert_yaxis()
    ax.axvline(tip["S0"], color=GREY, lw=0.8, ls=":")
    ax.axvline(tip["PLACEBO"], color=BLUE, lw=0.8, ls=":")
    ax.set_xlabel("Tipping point d50 (m), 95% bootstrap CI", fontsize=8, color=MUTED)
    ax.tick_params(labelsize=8, length=0)
    ax.grid(axis="x", color=GRID, lw=0.8)
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.tight_layout()
    fig.savefig("figures/fig_tipping.pdf")

    raw["words"] = raw.response.fillna("").map(lambda t: len(re.findall(r"\S+", t)))
    length = raw.groupby("scaffold").agg(tokens=("output_tokens", "median"), words=("words", "median"))
    out = {"counts": {s: {int(d): [int(r["sum"]), int(r["count"])] for d, r in tab.loc[s].iterrows()} for s in ORDER},
           "d50": {s: [round(tip[s]), round(ci[s][0]), round(ci[s][1])] for s in ORDER},
           "length": {s: [float(length.loc[s, "tokens"]), float(length.loc[s, "words"])] for s in ORDER},
           "format_failures": raw[~raw.format_ok].groupby("scaffold").size().to_dict()}
    json.dump(out, open("figures/numbers.json", "w"), indent=1)
    print(json.dumps(out["d50"]), json.dumps(out["length"]))


if __name__ == "__main__":
    main()
