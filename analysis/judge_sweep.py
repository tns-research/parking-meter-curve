"""Judge coding of the sweep studies (prereg: judge section, exploratory).

  python3 analysis/judge_sweep.py

S0 is pooled across Studies 1 and 2 (no drift between the two runs)."""

import json

import pandas as pd
from statsmodels.stats.proportion import proportion_confint

PAIRS = [("runs/sweep_s0s2.jsonl", "judgments/sweep_s0s2.jsonl"),
         ("runs/sweep_placebo.jsonl", "judgments/sweep_placebo.jsonl"),
         ("runs/sweep_s4s5.jsonl", "judgments/sweep_s4s5.jsonl"),
         ("runs/sweep_s1s3.jsonl", "judgments/sweep_s1s3.jsonl")]
FIELDS = ["spot_handling", "lateness_framing", "mentions_fine", "suggests_running", "final_choice"]


def cohen_kappa_score(a, b):
    a, b = list(a), list(b)
    cats = sorted(set(a) | set(b))
    po = sum(x == y for x, y in zip(a, b)) / len(a)
    pe = sum((a.count(c) / len(a)) * (b.count(c) / len(b)) for c in cats)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def read(path):
    try:
        return [json.loads(l) for l in open(path) if l.strip()]
    except FileNotFoundError:
        return []


def load():
    runs, judg = [], []
    for r, j in PAIRS:
        runs += read(r)
        judg += [x for x in read(j) if not x.get("is_error")]
    runs = pd.DataFrame(runs)
    runs = runs[~runs["is_error"].astype(bool) & runs["answer"].notna()]
    j = pd.DataFrame(judg)
    claude = j[j.judge == "claude"].drop_duplicates("trial_id")
    codex = j[j.judge == "codex"].drop_duplicates("trial_id")
    df = runs.merge(claude, on="trial_id", how="inner")
    return df, claude, codex


def share(sub, mask):
    k, n = int(mask.sum()), len(sub)
    if n == 0:
        return "n=0"
    lo, hi = proportion_confint(k, n, method="wilson")
    return f"{k}/{n} = {k / n:.0%} [{lo:.0%}, {hi:.0%}]"


def main():
    df, claude, codex = load()
    print("judged:", len(df), "| answer line vs judge final_choice disagree:",
          int((df.answer != df.final_choice).sum()))
    for s in ("S0", "PLACEBO", "S1", "S2", "S5"):
        g = df[df.scaffold == s]
        w, d = g[g.answer == "WALK"], g[g.answer == "DRIVE"]
        print(f"\n== {s} (n={len(g)}, WALK {len(w)}, DRIVE {len(d)})")
        print("  (1) WALK citing the spot as the reason:", share(w, w.spot_handling == "reason_to_walk"))
        print("  (2) DRIVE spot_handling:", d.spot_handling.value_counts().to_dict())
        print("  (3) late_is_impossible, all:", share(g, g.lateness_framing == "late_is_impossible"),
              "| among DRIVE:", share(d, d.lateness_framing == "late_is_impossible"))
        short = g[g.distance_m <= 100]
        print("      late_is_impossible at 25-100 m:", share(short, short.lateness_framing == "late_is_impossible"))
        print("      late_is_tolerable_risk, all:", share(g, g.lateness_framing == "late_is_tolerable_risk"))
        print("  mentions fine:", share(g, g.mentions_fine.astype(bool)),
              "| suggests running:", share(g, g.suggests_running.astype(bool)))
    both = claude.merge(codex, on="trial_id", suffixes=("_cl", "_cx"))
    print(f"\nClaude vs Codex agreement on {len(both)} responses (Cohen's kappa):")
    for f in FIELDS:
        a, b = both[f + "_cl"].astype(str), both[f + "_cx"].astype(str)
        print(f"  {f}: kappa={cohen_kappa_score(a, b):.2f}, raw agreement={(a == b).mean():.0%}")


if __name__ == "__main__":
    main()
