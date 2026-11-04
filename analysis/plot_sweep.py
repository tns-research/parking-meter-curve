"""Walk share by distance, per scaffold. python3 analysis/plot_sweep.py"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sweep import curve, d50, load

FILES = ["runs/sweep_s0s2.jsonl", "runs/sweep_placebo.jsonl", "runs/sweep_s4s5.jsonl"]
SERIES = {
    "S0": ("Sans scaffold", "#52514e", "o"),
    "PLACEBO": ("Placebo", "#2a78d6", "s"),
    "S2": ("S2", "#eb6834", "^"),
    "S4": ("S4", "#1baf7a", "D"),
    "S5": ("S5", "#6250d6", "v"),
}
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z**2 / n
    mid = (p + z**2 / (2 * n)) / d
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / d
    return mid - half, mid + half


def style(ax):
    ax.set_facecolor(SURFACE)
    ax.set_ylim(-3, 103)
    ax.set_xlim(0, 520)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0 %", "25 %", "50 %", "75 %", "100 %"])
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.axhline(50, color="#a8a79f", lw=0.9, ls=(0, (4, 3)))
    ax.tick_params(colors=MUTED, length=0, labelsize=10)
    for s in ax.spines.values():
        s.set_visible(False)


def main():
    raw = pd.concat([load(f) for f in FILES], ignore_index=True)
    df = raw[raw.format_ok].copy()
    df["walk"] = (df.answer == "WALK").astype(int)
    c = curve(df)
    table = df.groupby(["scaffold", "distance_m"]).walk.agg(["sum", "count"])
    tip = {s: d50(c.loc[s]["mean"]) for s in SERIES}

    fig = plt.figure(figsize=(12, 11), facecolor=SURFACE)
    gs = fig.add_gridspec(3, 2, height_ratios=[1.5, 1, 1], hspace=0.42, wspace=0.14,
                          left=0.07, right=0.98, top=0.89, bottom=0.06)
    ax = fig.add_subplot(gs[0, :])
    style(ax)
    for s, (name, col, mk) in SERIES.items():
        t = table.loc[s]
        ax.plot(t.index, 100 * t["sum"] / t["count"], color=col, lw=2, marker=mk, ms=8,
                mec=SURFACE, mew=1.5, label=f"{name} (bascule {tip[s]:.0f} m)")
    ax.legend(frameon=False, fontsize=11, labelcolor=INK, loc="upper right")
    ax.set_ylabel("Part de WALK", color=MUTED, fontsize=11)
    ax.set_xlabel("Distance de l'horodateur (m)", color=MUTED, fontsize=11)

    base = table.loc["S0"]
    for i, s in enumerate(["PLACEBO", "S2", "S4", "S5"]):
        a = fig.add_subplot(gs[1 + i // 2, i % 2])
        style(a)
        name, col, mk = SERIES[s]
        t = table.loc[s]
        for tb, cl, m in ((base, SERIES["S0"][1], "o"), (t, col, mk)):
            lo, hi = wilson(tb["sum"].values, tb["count"].values)
            a.fill_between(tb.index, 100 * lo, 100 * hi, color=cl, alpha=0.14, lw=0)
            a.plot(tb.index, 100 * tb["sum"] / tb["count"], color=cl, lw=2, marker=m, ms=7,
                   mec=SURFACE, mew=1.2)
        a.set_title(f"{name} contre sans scaffold : {tip['S0']:.0f} m → {tip[s]:.0f} m ({tip[s] - tip['S0']:+.0f} m)",
                    loc="left", color=INK, fontsize=12)
        if i % 2:
            a.set_yticklabels([])
        if i >= 2:
            a.set_xlabel("Distance (m)", color=MUTED, fontsize=11)

    fig.text(0.07, 0.955, "Toute consigne ajoutée repousse le passage à DRIVE, S2 et S5 le plus loin",
             fontsize=16, fontweight="bold", color=INK)
    fig.text(0.07, 0.925, "Parcmètre T6, Haiku 5.5, effort bas. 20 essais par point, 40 pour sans scaffold. "
             "Bonne réponse : WALK partout. Bandes : IC 95 % (Wilson).", fontsize=11, color=MUTED)
    fig.savefig("figures/sweep_curves.png", dpi=150, facecolor=SURFACE)
    print({k: round(v) for k, v in tip.items()})


if __name__ == "__main__":
    main()
