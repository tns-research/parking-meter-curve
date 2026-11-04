"""Checks that every flag we pass exists in the installed CLIs (no model call)."""
import shutil
import subprocess

import pytest

from ccb2.judge import claude_judge_command
from ccb2.runners import ClaudeCodeRunner, CodexRunner


def help_text(*cmd):
    return subprocess.run([*cmd, "--help"], capture_output=True, text=True, timeout=60).stdout


@pytest.mark.skipif(not shutil.which("claude"), reason="claude CLI missing")
def test_claude_flags_exist():
    h = help_text("claude")
    cmds = ClaudeCodeRunner("m", "low").command("P") + claude_judge_command("P")
    for flag in {c for c in cmds if c.startswith("--")}:
        assert flag in h, flag


@pytest.mark.skipif(not shutil.which("codex"), reason="codex CLI missing")
def test_codex_flags_exist():
    h = help_text("codex", "exec")
    for flag in {c for c in CodexRunner("m", "low").command("P", "o") if c.startswith("-")}:
        assert flag in h, flag
