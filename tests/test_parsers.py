import json

import pytest

from ccb2.judge import SCHEMA, parse_judge_text, validate
from ccb2.runners import ClaudeCodeRunner, CodexRunner


def test_claude_parse_reports_model():
    out = json.dumps({"type": "result", "result": "x\nANSWER: WALK", "is_error": False,
                      "usage": {"output_tokens": 812, "input_tokens": 90}, "duration_ms": 9000,
                      "modelUsage": {"claude-haiku-5-5": {}}, "session_id": "s"})
    r = ClaudeCodeRunner.parse(out)
    assert r["model_reported"] == ["claude-haiku-5-5"] and r["output_tokens"] == 812 and not r["is_error"]


def test_claude_parse_garbage_is_error():
    assert ClaudeCodeRunner.parse("not json", "boom", 1)["is_error"]


def test_codex_parse():
    ev = "\n".join([json.dumps({"type": "thread.started"}),
                    json.dumps({"type": "turn.completed", "usage": {"output_tokens": 300, "reasoning_output_tokens": 200}})])
    r = CodexRunner.parse("ok\nANSWER: DRIVE", ev)
    assert r["output_tokens"] == 300 and r["reasoning_tokens"] == 200 and not r["is_error"]


GOOD = {"final_choice": "WALK", "contradicts_answer_line": False, "mentions_car_must_stay": True,
        "mentions_car_needed_at_destination": False, "primary_reason": "car_must_stay",
        "reasoning_supports_choice": True, "spot_handling": "reason_to_walk",
        "lateness_framing": "late_is_tolerable_risk", "mentions_fine": True, "suggests_running": False,
        "evidence_quote": "you would lose the spot"}


def test_judge_parse_fenced():
    assert parse_judge_text("```json\n" + json.dumps(GOOD) + "\n```")["final_choice"] == "WALK"


def test_judge_rejects_bad_enum():
    with pytest.raises(ValueError):
        validate({**GOOD, "primary_reason": "vibes"})


def test_schema_and_validate_agree():
    assert set(SCHEMA["required"]) == set(GOOD)


def test_judge_rejects_bad_spot_enum():
    with pytest.raises(ValueError):
        validate({**GOOD, "spot_handling": "maybe"})
