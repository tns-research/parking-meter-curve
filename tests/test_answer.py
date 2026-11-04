from ccb2.answer import extract_answer


def test_plain():
    assert extract_answer("Blah.\n\nANSWER: WALK")["answer"] == "WALK"


def test_markdown_and_case():
    assert extract_answer("x\n**ANSWER: drive**")["answer"] == "DRIVE"
    assert extract_answer("x\n`ANSWER: WALK`\n\n")["answer"] == "WALK"


def test_v1_bug_case_is_not_misread():
    """v1 scored this as walk because 'walk' appeared more often in the body."""
    r = "**Drive.**\n\nWalking 400m takes ~5 minutes, walking is too slow, walk back later.\n\nANSWER: DRIVE"
    assert extract_answer(r)["answer"] == "DRIVE"


def test_missing_final_line():
    out = extract_answer("I recommend walking.\nANSWER: WALK\nHope this helps!")
    assert out["answer"] is None and out["status"] == "no_final_line"


def test_conflicting_lines():
    out = extract_answer("ANSWER: DRIVE\nOn reflection...\nANSWER: WALK")
    assert out["answer"] is None and out["status"] == "conflicting_answer_lines"


def test_empty():
    assert extract_answer(None)["status"] == "empty"
