"""Judge validation: agreement between Opus, Codex and the human coders.

  .venv/bin/python analysis/agreement.py judgments/core.jsonl validation/human_codes.csv

human_codes.csv columns: trial_id, coder, final_choice, mentions_car_must_stay,
primary_reason. Gate before any confirmatory analysis: Cohen's kappa >= 0.70
between Opus and the human consensus on mentions_car_must_stay and
final_choice (prereg/PREREG.md)."""

import json
import sys

import pandas as pd

FIELDS = ["final_choice", "mentions_car_must_stay", "primary_reason"]


def kappa(a: pd.Series, b: pd.Series) -> float:
    a, b = a.astype(str), b.astype(str)
    cats = sorted(set(a) | set(b))
    po = (a.values == b.values).mean()
    pe = sum((a == c).mean() * (b == c).mean() for c in cats)
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def main(judgments_path, human_path=None) -> None:
    j = pd.DataFrame([json.loads(l) for l in open(judgments_path) if l.strip()])
    j = j[~j["is_error"].astype(bool)]
    claude = j[j["judge"] == "claude"].set_index("trial_id")
    codex = j[j["judge"] == "codex"].set_index("trial_id")
    both = claude.join(codex, lsuffix="_opus", rsuffix="_codex", how="inner")
    print(f"Opus vs Codex (n={len(both)})")
    for f in FIELDS:
        print(f"  {f}: kappa={kappa(both[f + '_opus'], both[f + '_codex']):.3f}")

    if human_path:
        h = pd.read_csv(human_path)
        coders = sorted(h["coder"].unique())
        if len(coders) >= 2:
            a = h[h["coder"] == coders[0]].set_index("trial_id")
            b = h[h["coder"] == coders[1]].set_index("trial_id")
            hh = a.join(b, lsuffix="_a", rsuffix="_b", how="inner")
            print(f"Human vs human (n={len(hh)})")
            for f in FIELDS:
                print(f"  {f}: kappa={kappa(hh[f + '_a'], hh[f + '_b']):.3f}")
        consensus = h.groupby("trial_id")[FIELDS].agg(lambda s: s.mode().iloc[0])
        oh = claude.join(consensus, lsuffix="_opus", rsuffix="_human", how="inner")
        print(f"Opus vs human consensus (n={len(oh)})")
        for f in FIELDS:
            k = kappa(oh[f + "_opus"], oh[f + "_human"])
            gate = "" if f == "primary_reason" else ("  PASS" if k >= 0.70 else "  FAIL (gate 0.70)")
            print(f"  {f}: kappa={k:.3f}{gate}")


if __name__ == "__main__":
    main(*sys.argv[1:])
