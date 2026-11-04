"""Experimental design: expands a config into a list of trials.

A trial is one model call. Its id is a hash of its content, so a run can be
resumed without duplicates. Trial order is shuffled with a fixed seed, so
conditions are interleaved in time instead of run in blocks."""

import hashlib
import json
import random
from pathlib import Path

from .prompts import build_prompt

V2 = Path(__file__).resolve().parent.parent


def load_items(path: Path = V2 / "items" / "scenarios.json") -> dict:
    return json.loads(Path(path).read_text())


def load_scaffolds(path: Path = V2 / "scaffolds" / "scaffolds.json") -> dict:
    return json.loads(Path(path).read_text())["scaffolds"]


def load_config(path) -> dict:
    return json.loads(Path(path).read_text())


def trial_id(fields: dict) -> str:
    key = json.dumps(fields, sort_keys=True)
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def sweep_items(sweep: dict) -> dict:
    """One item per distance from a template, all keyed the same way."""
    scenarios = [{"id": f"{sweep['item']}_d{d}", "distance_m": d,
                  "q": sweep["template"].format(d=d)} for d in sweep["distances"]]
    return {"keys": {"q": sweep["key"]}, "scenarios": scenarios}


def expand(config: dict, items: dict | None = None, scaffolds: dict | None = None) -> list[dict]:
    if "sweep" in config:
        items = sweep_items(config["sweep"])
        config = {**config, "variants": ["q"]}
    items = items or load_items()
    scaffolds = scaffolds or load_scaffolds()
    keys = items["keys"]
    scenarios = items["scenarios"]
    if config.get("scenarios"):
        scenarios = [s for s in scenarios if s["id"] in config["scenarios"]]

    trials = []
    for m in config["models"]:
        for effort in m["efforts"]:
            for sc in scenarios:
                for variant in config["variants"]:
                    for cond in config["conditions"]:
                        scaffold_id, position = cond["scaffold"], cond.get("position", "prefix")
                        if scaffold_id == "S0":
                            position = "none"
                        for rep in range(1, config["reps"] + 1):
                            fields = {
                                "study": config["study"],
                                "backend": m["backend"], "model": m["model"], "effort": effort,
                                "scenario": sc["id"], "variant": variant,
                                "scaffold": scaffold_id, "position": position, "rep": rep,
                            }
                            prompt = build_prompt(
                                sc[variant], scaffolds[scaffold_id],
                                "prefix" if position == "none" else position,
                            )
                            if "distance_m" in sc:
                                fields["distance_m"] = sc["distance_m"]
                            trials.append({
                                "trial_id": trial_id(fields), **fields,
                                "key": keys[variant], "question": sc[variant], "prompt": prompt,
                            })
    random.Random(config.get("seed", 0)).shuffle(trials)
    return trials


def cell_counts(trials: list[dict]) -> dict:
    out: dict = {}
    for t in trials:
        k = (t["model"], t["effort"], t["variant"], t["scaffold"], t["position"])
        out[k] = out.get(k, 0) + 1
    return out
