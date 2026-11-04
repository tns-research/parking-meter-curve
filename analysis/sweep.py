"""Distance-sweep analysis (see prereg/PREREG.md, sweep section).

  python3 analysis/sweep.py runs/sweep_s0s2.jsonl [--sim]

Primary: Cochran-Mantel-Haenszel test of WALK vs DRIVE, S2 vs S0, stratified
by distance (a shift of the whole curve). Descriptive: tipping point d50
(log-distance interpolation of the cell WALK rates) and its bootstrap CI."""

import json
import sys

import numpy as np
import pandas as pd
from statsmodels.stats.contingency_tables import StratifiedTable


def load(path) -> pd.DataFrame:
    df = pd.DataFrame([json.loads(l) for l in open(path) if l.strip()])
    df = df[~df["is_error"].astype(bool)].copy()
    df["format_ok"] = df["answer"].notna()
    return df


def curve(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby(["scaffold", "distance_m"])["walk"].agg(["sum", "count", "mean"]).round(3)


def d50(rates: pd.Series) -> float:
    """First crossing below 0.5, interpolated on log distance. inf if the
    curve never drops below 0.5, the first distance if it starts below."""
    d, r = np.array(rates.index, float), rates.to_numpy(float)
    if r[0] < 0.5:
        return float(d[0])
    for i in range(1, len(r)):
        if r[i] < 0.5:
            x0, x1 = np.log(d[i - 1]), np.log(d[i])
            return float(np.exp(x0 + (r[i - 1] - 0.5) / (r[i - 1] - r[i]) * (x1 - x0)))
    return float("inf")


def cmh(df: pd.DataFrame, a: str, b: str) -> tuple[float, float]:
    tables = []
    for _, g in df[df["scaffold"].isin([a, b])].groupby("distance_m"):
        t = np.array([[((g.scaffold == s) & (g.walk == w)).sum() for w in (1, 0)] for s in (b, a)], float)
        if t.sum(axis=0).min() > 0:  # strata with only WALK or only DRIVE carry no information
            tables.append(t)
    if not tables:
        return float("nan"), 1.0
    st = StratifiedTable(tables)
    return st.oddsratio_pooled, st.test_null_odds(correction=True).pvalue


def boot_d50_diff(df, a, b, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    out = []
    cells = {k: g["walk"].to_numpy() for k, g in df.groupby(["scaffold", "distance_m"])}
    for _ in range(n):
        res = {}
        for s in (a, b):
            r = pd.Series({d: rng.choice(v, len(v)).mean() for (sc, d), v in cells.items() if sc == s}).sort_index()
            res[s] = d50(r)
        out.append(res[b] - res[a] if np.isfinite([res[a], res[b]]).all() else np.nan)
    out = np.array(out)
    return np.nanpercentile(out, [2.5, 97.5]), np.isnan(out).mean()


def main(path, base="S0") -> None:
    raw = load(path)
    print("format failures:", int((~raw["format_ok"]).sum()), "of", len(raw))
    df = raw[raw["format_ok"]].copy()
    df["walk"] = (df["answer"] == "WALK").astype(int)
    c = curve(df)
    print(c.unstack(0)["mean"].to_string(), "\n")
    for s in sorted(set(df["scaffold"]) - {base}):
        rates = {k: c.loc[k]["mean"] for k in (base, s)}
        a, b = d50(rates[base]), d50(rates[s])
        orr, p = cmh(df, base, s)
        ci, undefined = boot_d50_diff(df, base, s)
        print(f"{s} vs {base}: CMH OR(WALK)={orr:.2f} p={p:.4g} | d50 {base}={a:.0f} m, {s}={b:.0f} m, "
              f"diff={b - a:+.0f} m, 95% CI [{ci[0]:+.0f}, {ci[1]:+.0f}] (undefined in {undefined:.0%} of resamples)")
        sens = raw.copy()
        sens["walk"] = (sens["answer"] == "WALK").astype(int)
        print(f"  sensitivity (format failures = DRIVE): p={cmh(sens, base, s)[1]:.4g}")


def simulate(n_sims=2000, reps=10, seed=1):
    """Power of the primary test for given tipping-point shifts."""
    rng = np.random.default_rng(seed)
    dists = np.array([25, 50, 100, 150, 200, 250, 300, 350, 400, 500])
    slope = 4.0  # logit per doubling of distance, steep as in the probes
    for shift in (25, 50, 100):
        hits = 0
        for _ in range(n_sims):
            rows = []
            for s, mid in (("S0", 200), ("S2", 200 + shift)):
                p = 1 / (1 + np.exp(slope * np.log2(dists / mid)))
                for d, pi in zip(dists, p):
                    rows += [{"scaffold": s, "distance_m": d, "walk": w} for w in rng.random(reps) < pi]
            df = pd.DataFrame(rows)
            df["walk"] = df["walk"].astype(int)
            hits += cmh(df, "S0", "S2")[1] < 0.05
        print(f"d50 200 -> {200 + shift} m: power {hits / n_sims:.2f}")


if __name__ == "__main__":
    simulate() if "--sim" in sys.argv else main(sys.argv[1])
