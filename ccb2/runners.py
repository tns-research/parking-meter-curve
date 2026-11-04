"""Model backends. All go through subscriptions (Claude Code, Codex CLI), never
a paid API key. Each runner returns a flat dict that is stored as is."""

import json
import subprocess
import tempfile
import time
from pathlib import Path

from .prompts import SYSTEM_PROMPT


class ClaudeCodeRunner:
    """`claude -p` with a fixed minimal system prompt, no tools, no MCP, no
    user/project settings and no session persistence, launched from an empty
    directory so no CLAUDE.md is picked up."""

    name = "claude_code"

    def __init__(self, model: str, effort: str, timeout: int = 600):
        self.model, self.effort, self.timeout = model, effort, timeout

    def command(self, prompt: str) -> list[str]:
        return [
            "claude", "-p", prompt,
            "--model", self.model,
            "--effort", self.effort,
            "--system-prompt", SYSTEM_PROMPT,
            "--output-format", "json",
            "--tools", "",
            "--strict-mcp-config",
            "--setting-sources", "",
            "--no-session-persistence",
        ]

    def run(self, prompt: str) -> dict:
        with tempfile.TemporaryDirectory(prefix="ccb2-") as cwd:
            t0 = time.time()
            r = subprocess.run(self.command(prompt), cwd=cwd, capture_output=True,
                               text=True, timeout=self.timeout)
            wall = time.time() - t0
        return self.parse(r.stdout, r.stderr, r.returncode, wall)

    @staticmethod
    def parse(stdout: str, stderr: str = "", returncode: int = 0, wall: float = 0.0) -> dict:
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return {"response": None, "is_error": True,
                    "error": f"rc={returncode} stdout={stdout[:300]} stderr={stderr[:300]}"}
        usage = data.get("usage") or {}
        return {
            "response": data.get("result"),
            "is_error": bool(data.get("is_error")) or returncode != 0,
            "error": data.get("result") if data.get("is_error") else None,
            "model_reported": sorted((data.get("modelUsage") or {}).keys()),
            "output_tokens": usage.get("output_tokens"),
            "input_tokens": usage.get("input_tokens"),
            "duration_ms": data.get("duration_ms"),
            "wall_s": round(wall, 2),
            "session_id": data.get("session_id"),
        }


class CodexRunner:
    """`codex exec` on the ChatGPT subscription, read-only sandbox, ephemeral.
    Codex keeps its own agent system prompt: report it as an agent condition."""

    name = "codex"

    def __init__(self, model: str, effort: str, timeout: int = 600):
        self.model, self.effort, self.timeout = model, effort, timeout

    def command(self, prompt: str, out_file: str) -> list[str]:
        return [
            "codex", "exec",
            "-m", self.model,
            "-c", f"model_reasoning_effort={self.effort}",
            "--sandbox", "read-only",
            "--skip-git-repo-check",
            "--ephemeral",
            "--json",
            "-o", out_file,
            prompt,
        ]

    def run(self, prompt: str) -> dict:
        with tempfile.TemporaryDirectory(prefix="ccb2-") as cwd:
            out = str(Path(cwd) / "last.txt")
            t0 = time.time()
            r = subprocess.run(self.command(prompt, out), cwd=cwd, capture_output=True,
                               text=True, timeout=self.timeout, stdin=subprocess.DEVNULL)
            wall = time.time() - t0
            text = Path(out).read_text() if Path(out).exists() else None
        return self.parse(text, r.stdout, r.stderr, r.returncode, wall)

    @staticmethod
    def parse(text, events: str, stderr: str = "", returncode: int = 0, wall: float = 0.0) -> dict:
        output_tokens = reasoning_tokens = None
        models = set()
        for line in events.splitlines():
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(ev.get("model"), str):
                models.add(ev["model"])
            usage = ev.get("usage") or {}
            if "output_tokens" in usage:
                output_tokens = usage["output_tokens"]
                reasoning_tokens = usage.get("reasoning_output_tokens", reasoning_tokens)
        failed = returncode != 0 or not text
        return {
            "response": text,
            "is_error": failed,
            "error": f"rc={returncode} stderr={stderr[-300:]}" if failed else None,
            "model_reported": sorted(models),
            "output_tokens": output_tokens,
            "reasoning_tokens": reasoning_tokens,
            "wall_s": round(wall, 2),
        }


class FakeRunner:
    """Offline runner for tests and dry runs. Answers DRIVE whenever the
    prompt contains a scaffold keyword, WALK otherwise."""

    name = "fake"

    def __init__(self, model: str = "fake", effort: str = "low", **_):
        self.model, self.effort = model, effort

    def run(self, prompt: str) -> dict:
        drive = any(w in prompt for w in ("means-end", "mental simulation", "causal system"))
        answer = "DRIVE" if drive else "WALK"
        return {"response": f"Reasoning.\n\nANSWER: {answer}", "is_error": False, "error": None,
                "model_reported": [self.model], "output_tokens": 10, "wall_s": 0.0}


RUNNERS = {"claude_code": ClaudeCodeRunner, "codex": CodexRunner, "fake": FakeRunner}


def make_runner(backend: str, model: str, effort: str):
    return RUNNERS[backend](model=model, effort=effort)
