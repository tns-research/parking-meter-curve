"""LLM judge for the reasoning, blind to the condition.

The judge sees the bare question (never the scaffold) and the response. It
does not receive the answer key: it reports what the response says and why,
and the analysis compares that to the key. Opus via Claude Code is the main
judge; Codex re-judges a random 20% to check for same-family bias."""

import json
import subprocess
import tempfile
from pathlib import Path

JUDGE_MODEL = "claude-opus-5-5"
JUDGE_EFFORT = "medium"

REASONS = [
    "car_must_stay",
    "car_needed_at_destination",
    "distance_or_time",
    "effort_or_convenience",
    "cost_or_environment",
    "other",
]

SPOT = ["not_mentioned", "reason_to_walk", "plans_to_retake_spot", "mentioned_but_dismissed"]
LATENESS = ["not_discussed", "late_is_impossible", "late_is_tolerable_risk"]

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "final_choice", "contradicts_answer_line", "mentions_car_must_stay",
        "mentions_car_needed_at_destination", "primary_reason",
        "reasoning_supports_choice", "spot_handling", "lateness_framing",
        "mentions_fine", "suggests_running", "evidence_quote",
    ],
    "properties": {
        "final_choice": {"type": "string", "enum": ["WALK", "DRIVE", "UNCLEAR"]},
        "contradicts_answer_line": {"type": "boolean"},
        "mentions_car_must_stay": {"type": "boolean"},
        "mentions_car_needed_at_destination": {"type": "boolean"},
        "primary_reason": {"type": "string", "enum": REASONS},
        "reasoning_supports_choice": {"type": "boolean"},
        "spot_handling": {"type": "string", "enum": SPOT},
        "lateness_framing": {"type": "string", "enum": LATENESS},
        "mentions_fine": {"type": "boolean"},
        "suggests_running": {"type": "boolean"},
        "evidence_quote": {"type": "string"},
    },
}

RUBRIC = """You are coding a response from an AI assistant for a research study. Do not judge whether the advice is good. Report only what the response says.

Fields:
- final_choice: the option the response recommends overall, read from the whole text (WALK, DRIVE, or UNCLEAR if it never commits).
- contradicts_answer_line: true if the body of the response recommends one option but its final "ANSWER:" line says the other, or if the final line is missing.
- mentions_car_must_stay: true only if the response explicitly says that moving the car would undo or endanger something the person's goal depends on (for example losing the parking spot, a place in a queue, a charging session, a meeting or appointment location).
- mentions_car_needed_at_destination: true only if the response explicitly says the car itself has to be at the destination for the goal.
- primary_reason: the single reason the response gives most weight to when choosing: car_must_stay, car_needed_at_destination, distance_or_time, effort_or_convenience, cost_or_environment, other.
- reasoning_supports_choice: true if the reasons given lead to the recommended option without contradicting it.
- spot_handling: how the response treats the fact that driving moves the car out of the parking spot the payment is for. not_mentioned: never raised. reason_to_walk: raised as a reason not to drive. plans_to_retake_spot: raised, and the plan is to drive and come back to the same spot. mentioned_but_dismissed: raised, then set aside or outweighed without a plan to come back.
- lateness_framing: how the response treats arriving at the machine after the time runs out. not_discussed. late_is_impossible: arriving late is treated as ruling an option out (infeasible, fails, cannot make it). late_is_tolerable_risk: arriving late is treated as a risk to weigh (a possible ticket or fine, a small delay).
- mentions_fine: true if the response mentions a parking ticket, fine or penalty.
- suggests_running: true if the response suggests running, jogging or walking fast.
- evidence_quote: a verbatim quote of at most 25 words from the response that best supports primary_reason.

Return only the JSON object."""


def judge_prompt(question: str, response: str) -> str:
    return (
        f"{RUBRIC}\n\n=== QUESTION ASKED TO THE ASSISTANT ===\n{question}\n\n"
        f"=== ASSISTANT RESPONSE ===\n{response}\n=== END ==="
    )


def validate(obj: dict) -> dict:
    missing = [k for k in SCHEMA["required"] if k not in obj]
    if missing:
        raise ValueError(f"judge output missing {missing}")
    if obj["final_choice"] not in ("WALK", "DRIVE", "UNCLEAR"):
        raise ValueError("bad final_choice")
    if obj["primary_reason"] not in REASONS:
        raise ValueError("bad primary_reason")
    if obj["spot_handling"] not in SPOT or obj["lateness_framing"] not in LATENESS:
        raise ValueError("bad spot_handling or lateness_framing")
    return {k: obj[k] for k in SCHEMA["required"]}


def parse_judge_text(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[1]
    start, end = text.find("{"), text.rfind("}")
    return validate(json.loads(text[start:end + 1]))


def claude_judge_command(prompt: str) -> list[str]:
    return [
        "claude", "-p", prompt,
        "--model", JUDGE_MODEL,
        "--effort", JUDGE_EFFORT,
        "--system-prompt", "You are a careful research coder. Follow the rubric exactly.",
        "--output-format", "json",
        "--json-schema", json.dumps(SCHEMA),
        "--tools", "",
        "--strict-mcp-config",
        "--setting-sources", "",
        "--no-session-persistence",
    ]


def run_claude_judge(question: str, response: str, timeout: int = 600) -> dict:
    with tempfile.TemporaryDirectory(prefix="ccb2-judge-") as cwd:
        r = subprocess.run(claude_judge_command(judge_prompt(question, response)),
                           cwd=cwd, capture_output=True, text=True, timeout=timeout)
    data = json.loads(r.stdout)
    if data.get("is_error"):
        raise RuntimeError(str(data.get("result"))[:300])
    payload = data.get("structured_output") or data.get("result")
    obj = payload if isinstance(payload, dict) else parse_judge_text(payload)
    return {"judge": "claude", "judge_model_reported": sorted((data.get("modelUsage") or {}).keys()),
            **validate(obj)}


def run_codex_judge(question: str, response: str, model: str, timeout: int = 600) -> dict:
    with tempfile.TemporaryDirectory(prefix="ccb2-judge-") as cwd:
        schema_file, out = Path(cwd) / "schema.json", Path(cwd) / "last.txt"
        schema_file.write_text(json.dumps(SCHEMA))
        cmd = ["codex", "exec", "-m", model, "--sandbox", "read-only", "--skip-git-repo-check",
               "--ephemeral", "--output-schema", str(schema_file), "-o", str(out),
               judge_prompt(question, response)]
        subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                       stdin=subprocess.DEVNULL)
        text = out.read_text() if out.exists() else ""
    return {"judge": "codex", "judge_model_reported": [model], **parse_judge_text(text)}
