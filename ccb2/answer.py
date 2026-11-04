"""Deterministic extraction of the forced final answer line.

Only the last non-empty line counts. Anything else (missing line, extra text,
two different ANSWER lines) is a format failure, returned as None, and goes
to the judge and to human review instead of being guessed."""

import re

_LINE = re.compile(r"^ANSWER:\s*(WALK|DRIVE)\.?$", re.IGNORECASE)
_ANY = re.compile(r"ANSWER:\s*\**\s*(WALK|DRIVE)", re.IGNORECASE)


def _clean(line: str) -> str:
    return re.sub(r"[*_`>#]", "", line).strip()


def extract_answer(response: str | None) -> dict:
    if not response or not response.strip():
        return {"answer": None, "status": "empty"}
    lines = [l for l in response.splitlines() if l.strip()]
    m = _LINE.match(_clean(lines[-1]))
    mentioned = {x.upper() for x in _ANY.findall(response)}
    if not m:
        return {"answer": None, "status": "no_final_line"}
    answer = m.group(1).upper()
    if len(mentioned) > 1:
        return {"answer": None, "status": "conflicting_answer_lines"}
    return {"answer": answer, "status": "ok"}
