"""`.asqav.json` is a claim about the code, so the code is checked against it.

The ASQAV scan (`vendor/asqav-compliance`, our fork) decides each governance
category by matching patterns. The repository config teaches it how this
codebase spells an audit trail. A pattern that matched a comment, or that no
longer matches anything, would turn the scan green for the wrong reason — the
exact failure the config exists to fix — so each one must name a real call, in
code, not prose. And any module that talks to a model SDK directly must be
covered by the same rule the scanner applies, so a new agent that bypasses the
ledger fails here before the report ever runs.
"""

from __future__ import annotations

import io
import json
import re
import tokenize

import pytest
from conftest import REPO_ROOT

CONFIG = REPO_ROOT / ".asqav.json"
SRC = REPO_ROOT / "platform" / "src"
#: The scanner's own test for "this file is agent code" (vendor/asqav-compliance src/scanner.ts).
AGENT_IMPORT = re.compile(
    r"^\s*(?:import\s+(?:langchain|crewai|openai|anthropic|autogen|google\.generativeai|smolagents|llama_index|"
    r"haystack|semantic_kernel|dspy|pydantic_ai))|^\s*(?:from\s+(?:langchain|crewai|openai|anthropic|autogen|"
    r"google\.generativeai|smolagents|llama_index|haystack|semantic_kernel|dspy|pydantic_ai)[\s.])", re.M)


def _config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _code_only(text: str) -> str:
    """Source with comments and string literals (docstrings included) blanked
    in place, so what remains is exactly the code, at its own positions."""
    lines = text.splitlines(keepends=True)
    try:
        spans = [(t.start, t.end) for t in tokenize.generate_tokens(io.StringIO(text).readline)
                 if t.type in (tokenize.COMMENT, tokenize.STRING)]
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return text
    for (r0, c0), (r1, c1) in spans:
        for r in range(r0, r1 + 1):
            line = lines[r - 1]
            a = c0 if r == r0 else 0
            b = c1 if r == r1 else len(line.rstrip("\n"))
            lines[r - 1] = line[:a] + " " * (b - a) + line[b:]
    return "".join(lines)


def _excluded(rel: str, globs: list[str]) -> bool:
    def rx(g: str) -> re.Pattern[str]:
        out, i = "", 0
        while i < len(g):
            if g[i] == "*" and g[i + 1:i + 2] == "*":
                i += 1
                if g[i + 1:i + 2] == "/":
                    i += 1
                    out += "(?:.*/)?"
                else:
                    out += ".*"
            elif g[i] == "*":
                out += "[^/]*"
            elif g[i] == "?":
                out += "[^/]"
            else:
                out += re.escape(g[i])
            i += 1
        return re.compile(f"^{out}$")

    return any(rx(g).match(rel) for g in globs)


def test_the_config_is_valid_and_every_pattern_compiles() -> None:
    cfg = _config()
    assert cfg.get("version") == 1
    known = {"auditTrail", "policyEnforcement", "revocation", "humanOversight", "errorHandling"}
    assert set(cfg.get("patterns", {})) <= known
    for patterns in cfg["patterns"].values():
        for p in patterns:
            re.compile(p)
    assert all(isinstance(g, str) and g for g in cfg.get("exclude", []))


@pytest.mark.parametrize("pattern", _config()["patterns"]["auditTrail"])
def test_every_audit_pattern_names_a_real_call_not_a_word(pattern: str) -> None:
    """Matched against code with comments and strings stripped: a pattern that
    only a docstring satisfies claims a control nobody calls."""
    rx = re.compile(pattern)
    hits = [p for p in SRC.rglob("*.py") if rx.search(_code_only(p.read_text(encoding="utf-8", errors="replace")))]
    assert hits, f"`{pattern}` matches no call in platform/src — remove it or fix it"


def test_every_module_that_calls_a_model_sdk_writes_the_audit_record() -> None:
    """The scanner's own rule, applied with our vocabulary to every module it
    would scan: import a model SDK, and the file must also write to the trace /
    provenance record. A module that calls a model around the ledger fails here."""
    cfg = _config()
    audit = [re.compile(p) for p in cfg["patterns"]["auditTrail"]]
    missing = []
    for root in (REPO_ROOT / "platform", REPO_ROOT / "groups"):
        for path in root.rglob("*.py"):
            rel = path.relative_to(REPO_ROOT).as_posix()
            if any(part in {"node_modules", ".venv", "__pycache__", "build", "dist"} for part in path.parts):
                continue
            if _excluded(rel, cfg.get("exclude", [])):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if AGENT_IMPORT.search(text) and not any(rx.search(_code_only(text)) for rx in audit):
                missing.append(rel)
    assert not missing, f"model SDK used without writing the audit record: {missing}"


def test_tests_are_not_scored_as_agent_code() -> None:
    assert _excluded("platform/tests/gate/test_loops.py", _config()["exclude"])
    assert not _excluded("platform/src/pf/agents/base.py", _config()["exclude"])
