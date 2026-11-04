import json
from pathlib import Path

from ccb2.design import V2, load_scaffolds


def test_scaffold_lengths_matched():
    sc = load_scaffolds()
    real = [len(sc[k].split()) for k in ("S2", "S4", "S5")]
    mean = sum(real) / len(real)
    for k in ("PLACEBO", "PRECOND"):
        assert abs(len(sc[k].split()) - mean) / mean <= 0.20, k


def test_scaffolds_match_v1_verbatim():
    v1 = {x["id"]: x["text"] for x in json.loads((V2 / "provenance" / "v1_scaffolds.json").read_text())}
    sc = load_scaffolds()
    for k in ("S1", "S2", "S3", "S4", "S5"):
        assert sc[k] == v1[k]
