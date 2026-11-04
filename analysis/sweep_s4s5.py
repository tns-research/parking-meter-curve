"""Study 3 and 4 analysis (see prereg/PREREG.md, Studies 3 and 4).

  python3 analysis/sweep_s4s5.py            # Study 3: S4, S5
  python3 analysis/sweep_s4s5.py S1 S3      # Study 4: S1, S3

Primary: S4 and S5 vs the S0 of Studies 1 and 2 pooled, CMH by distance,
Bonferroni alpha 0.025 per test. Secondary: S4 and S5 vs PLACEBO and vs S2."""

import sys

import pandas as pd

from sweep import boot_d50_diff, cmh, curve, d50, load

FILES = ["runs/sweep_s0s2.jsonl", "runs/sweep_placebo.jsonl", "runs/sweep_s4s5.jsonl", "runs/sweep_s1s3.jsonl"]


def main(targets=("S4", "S5")):
    from pathlib import Path
    raw = pd.concat([load(f) for f in FILES if Path(f).exists()], ignore_index=True)
    print("format failures by scaffold:", raw[~raw.format_ok].groupby("scaffold").size().to_dict())
    df = raw[raw.format_ok].copy()
    df["walk"] = (df.answer == "WALK").astype(int)
    c = curve(df)
    print(c.unstack(0)["mean"].to_string(), "\n")
    for base, label in (("S0", "PRIMARY, alpha 0.025"), ("PLACEBO", "secondary, crosses run windows"),
                        ("S2", "secondary, crosses run windows")):
        for s in targets:
            a, b = d50(c.loc[base]["mean"]), d50(c.loc[s]["mean"])
            orr, p = cmh(df, base, s)
            ci, undefined = boot_d50_diff(df, base, s)
            print(f"[{label}] {s} vs {base}: CMH OR(WALK)={orr:.2f} p={p:.4g} | d50 {base}={a:.0f} m, {s}={b:.0f} m, "
                  f"diff={b - a:+.0f} m, 95% CI [{ci[0]:+.0f}, {ci[1]:+.0f}] (undefined in {undefined:.0%})")


if __name__ == "__main__":
    main(tuple(sys.argv[1:]) or ("S4", "S5"))
