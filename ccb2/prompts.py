"""Prompt assembly. The answer instruction is always the last block, so the
scaffold position (prefix or suffix) only moves the scaffold relative to the
question."""

SYSTEM_PROMPT = "You are a helpful assistant."

ANSWER_INSTRUCTION = (
    "You must choose exactly one of the two options. "
    "End your response with a final line that is exactly `ANSWER: WALK` or `ANSWER: DRIVE`."
)

POSITIONS = ("prefix", "suffix")


def build_prompt(question: str, scaffold: str | None, position: str = "prefix") -> str:
    if position not in POSITIONS:
        raise ValueError(f"unknown position {position!r}")
    if not scaffold:
        blocks = [question]
    elif position == "prefix":
        blocks = [scaffold, question]
    else:
        blocks = [question, scaffold]
    return "\n\n".join(blocks + [ANSWER_INSTRUCTION])
