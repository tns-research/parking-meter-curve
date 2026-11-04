import json

from ccb2.design import V2, expand, load_config, load_scaffolds
from ccb2.prompts import ANSWER_INSTRUCTION


def test_sweep_design():
    trials = expand(load_config(V2 / "config" / "sweep_s0s2.json"))
    assert len(trials) == 400 and len({t["trial_id"] for t in trials}) == 400
    cells = {}
    for t in trials:
        cells[(t["distance_m"], t["scaffold"])] = cells.get((t["distance_m"], t["scaffold"]), 0) + 1
        assert t["key"] == "WALK" and t["model"] == "claude-haiku-5-5" and t["effort"] == "low"
        assert f"is {t['distance_m']} meters away" in t["prompt"]
        assert t["prompt"].endswith(ANSWER_INSTRUCTION)
        assert t["prompt"].startswith(load_scaffolds()["S2"]) == (t["scaffold"] == "S2")
    assert set(cells.values()) == {20} and len(cells) == 20
    first = [(t["distance_m"], t["scaffold"]) for t in trials[:20]]
    assert first != sorted(first)


def test_sweep_template_is_v1_t6():
    cfg = load_config(V2 / "config" / "sweep_s0s2.json")
    assert cfg["sweep"]["template"].format(d=400) == (
        "My parking meter expires in 3 minutes. The meter machine is 400 meters away. "
        "There is no parking app available. You must choose one: should I walk or drive "
        "to extend my parking time?")
