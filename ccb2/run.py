"""CLI.

  python -m ccb2.run plan     --config config/sweep_s0s2.json
  python -m ccb2.run dry-run  --config config/sweep_s0s2.json --limit 3
  python -m ccb2.run execute  --config config/sweep_s0s2.json --i-have-approval
  python -m ccb2.run judge    --config config/sweep_s0s2.json --i-have-approval [--codex-share 0.2]

`execute` and `judge` spend subscription quota. They refuse to start unless
--i-have-approval is passed AND the environment variable CCB2_ALLOW_RUN=1 is
set, except with the offline `fake` backend."""

import argparse
import concurrent.futures
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path

from . import judge, store
from .answer import extract_answer
from .design import V2, cell_counts, expand, load_config
from .runners import make_runner


def runs_path(config: dict) -> Path:
    return V2 / "runs" / f"{config['study']}.jsonl"


def judgments_path(config: dict) -> Path:
    return V2 / "judgments" / f"{config['study']}.jsonl"


def guard(config: dict, approved: bool) -> None:
    if all(m["backend"] == "fake" for m in config["models"]):
        return
    if not approved or os.environ.get("CCB2_ALLOW_RUN") != "1":
        sys.exit("Refused: this spends subscription quota. Needs --i-have-approval and CCB2_ALLOW_RUN=1.")


def cmd_plan(config: dict, **_) -> None:
    trials = expand(config)
    print(f"study={config['study']} trials={len(trials)}")
    for k, n in sorted(cell_counts(trials).items()):
        print("  ", " | ".join(map(str, k)), n)
    done = store.done_ids(runs_path(config))
    print(f"already done: {len(done & {t['trial_id'] for t in trials})}")


def cmd_dry_run(config: dict, limit: int = 3, **_) -> None:
    for t in expand(config)[:limit]:
        runner = make_runner(t["backend"], t["model"], t["effort"])
        print("=" * 70)
        print({k: t[k] for k in ("trial_id", "model", "effort", "scenario", "variant", "scaffold", "position", "key")})
        print(t["prompt"])
        if hasattr(runner, "command"):
            cmd = runner.command(t["prompt"]) if runner.name == "claude_code" else runner.command(t["prompt"], "<out>")
            print("CMD:", [c if c != t["prompt"] else "<prompt>" for c in cmd])


def _one(t: dict, retries: int = 3) -> dict:
    runner = make_runner(t["backend"], t["model"], t["effort"])
    res = {}
    for attempt in range(1, retries + 1):
        try:
            res = runner.run(t["prompt"])
        except Exception as e:  # timeout, CLI crash
            res = {"response": None, "is_error": True, "error": f"{type(e).__name__}: {e}"}
        if not res.get("is_error"):
            break
        time.sleep(15 * attempt)
    parsed = extract_answer(res.get("response"))
    return {**t, **res, "attempt": attempt, "answer": parsed["answer"],
            "answer_status": parsed["status"],
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def cmd_execute(config: dict, approved: bool = False, workers: int = 4, max_calls: int | None = None, **_) -> None:
    guard(config, approved)
    out = runs_path(config)
    done = store.done_ids(out)
    todo = [t for t in expand(config) if t["trial_id"] not in done][:max_calls]
    print(f"{len(todo)} calls to run -> {out}", flush=True)
    stats = Counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for i, rec in enumerate(ex.map(_one, todo), 1):
            store.append(out, rec)
            stats["error" if rec.get("is_error") else rec["answer_status"]] += 1
            if i % 10 == 0 or i == len(todo):
                print(f"[{i}/{len(todo)}] {dict(stats)}", flush=True)


def cmd_judge(config: dict, approved: bool = False, workers: int = 3, codex_share: float = 0.2,
              codex_model: str = "gpt-5.6-sol", max_calls: int | None = None, **_) -> None:
    guard(config, approved)
    out = judgments_path(config)
    have = {(r["trial_id"], r["judge"]) for r in store.read(out) if not r.get("is_error")}
    runs = [r for r in store.read(runs_path(config)) if not r.get("is_error") and r.get("response")]
    if config.get("judge_scaffolds"):
        runs = [r for r in runs if r.get("scaffold") in config["judge_scaffolds"]]
    rng = random.Random(config.get("seed", 0) + 1)
    jobs = []
    for r in runs:
        if (r["trial_id"], "claude") not in have:
            jobs.append((r, "claude"))
        if rng.random() < codex_share and (r["trial_id"], "codex") not in have:
            jobs.append((r, "codex"))
    jobs = jobs[:max_calls]
    print(f"{len(jobs)} judge calls -> {out}", flush=True)

    def one(job):
        r, who = job
        try:
            j = (judge.run_claude_judge(r["question"], r["response"]) if who == "claude"
                 else judge.run_codex_judge(r["question"], r["response"], codex_model))
            return {"trial_id": r["trial_id"], **j, "is_error": False}
        except Exception as e:
            return {"trial_id": r["trial_id"], "judge": who, "is_error": True, "error": f"{type(e).__name__}: {e}"}

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for i, rec in enumerate(ex.map(one, jobs), 1):
            store.append(out, rec)
            if i % 10 == 0 or i == len(jobs):
                print(f"[{i}/{len(jobs)}]", flush=True)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="ccb2")
    p.add_argument("command", choices=["plan", "dry-run", "execute", "judge"])
    p.add_argument("--config", required=True)
    p.add_argument("--limit", type=int, default=3)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--max-calls", type=int)
    p.add_argument("--codex-share", type=float, default=0.2)
    p.add_argument("--i-have-approval", dest="approved", action="store_true")
    a = p.parse_args(argv)
    config = load_config(a.config)
    fn = {"plan": cmd_plan, "dry-run": cmd_dry_run, "execute": cmd_execute, "judge": cmd_judge}[a.command]
    fn(config, limit=a.limit, workers=a.workers, max_calls=a.max_calls,
       codex_share=a.codex_share, approved=a.approved)


if __name__ == "__main__":
    main()
