"""The trace log, and the live agent paths driven by a fake client.

Two things are pinned here. First, that every agentic step writes what a
person needs when the answer is wrong: intent, understanding, the request,
the response, each tool call and each deterministic step. Second, that the
live paths — the structured `call()` and the tool-use loop in `ask` — run end
to end against an injected client, so a prompt change can be exercised in CI
without a credential and a trace can be read back from it.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pf import trace
from pf.agents import base
from pf.agents.loops import Diagnosis, triage_failures
from pf.loops import actions
from pf.loops.runner import LoopRun, LoopSpec, run_loop


# ---------------------------------------------------------------- fakes ----
class FakeUsage(SimpleNamespace):
    pass


def _usage(i: int = 100, o: int = 20) -> Any:
    return SimpleNamespace(input_tokens=i, output_tokens=o,
                           cache_read_input_tokens=0, cache_creation_input_tokens=0)


class FakeParseClient:
    """`messages.parse` returns a fixed typed object."""

    def __init__(self, parsed: Any) -> None:
        self.parsed = parsed
        self.calls: list[dict[str, Any]] = []
        self.messages = self

    def parse(self, **kw: Any) -> Any:
        self.calls.append(kw)
        return SimpleNamespace(parsed_output=self.parsed, usage=_usage(),
                               stop_reason="end_turn")


class FakeToolClient:
    """`messages.create` replays a script of tool_use turns, then final_answer."""

    def __init__(self, script: list[list[dict[str, Any]]]) -> None:
        self.script = list(script)
        self.calls: list[dict[str, Any]] = []
        self.messages = self

    def create(self, **kw: Any) -> Any:
        self.calls.append(kw)
        blocks = [SimpleNamespace(type="tool_use", id=f"t{i}", name=b["name"], input=b["input"])
                  for i, b in enumerate(self.script.pop(0))]
        return SimpleNamespace(content=blocks, usage=_usage(), stop_reason="tool_use")


@pytest.fixture
def repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    pdir = root / "groups" / "g" / "projects" / "p"
    (root / "platform").mkdir(parents=True)
    (root / "groups" / "g" / "ontology").mkdir(parents=True)
    (pdir / "transform" / "models").mkdir(parents=True)
    (root / "gate.yaml").write_text("denylist: []\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root, pdir


@pytest.fixture(autouse=True)
def _reset_client():
    yield
    base.set_client(None)


# --------------------------------------------------------------- trace ----
def test_trace_writes_jsonl_and_index(tmp_path: Path) -> None:
    with trace.start(tmp_path, "command", "demo", group="g", project="p") as tr:
        tr.intent("do a thing", agent="x")
        tr.understanding("the thing is y")
        tr.step("gate", "passed", verdicts=[])
        tr.tool_call("query_metrics", {"metrics": ["revenue"]})
        tr.tool_result("query_metrics", "api_key = SECRET123 and rows")
    rows = trace.read(tmp_path, tr.id)
    types = [r["type"] for r in rows]
    assert types == ["start", "intent", "understanding", "step", "tool_call",
                     "tool_result", "outcome"]
    assert rows[-1]["outcome"] == "ok"
    assert "SECRET123" not in json.dumps(rows)           # redacted
    idx = trace.index(tmp_path)
    assert idx[-1]["run"] == tr.id and idx[-1]["kind"] == "command"
    assert "▶ command demo" in trace.render(rows)


def test_trace_records_errors_and_nesting(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError), trace.start(tmp_path, "command", "outer") as outer:
        inner = trace.start(tmp_path, "agent", "inner")
        assert inner.parent == outer.id
        inner.close()
        raise RuntimeError("boom")
    rows = trace.read(tmp_path, outer.id)
    assert rows[-2]["type"] == "error" and "boom" in rows[-2]["error"]
    assert rows[-1]["outcome"] == "error"


def test_trace_is_silent_outside_a_run() -> None:
    trace.get().intent("nothing happens")     # no exception, no file


def test_trace_can_be_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PF_TRACE", "0")
    with trace.start(tmp_path, "command", "x") as tr:
        tr.step("s")
    assert not (tmp_path / "logs").exists()


# ------------------------------------------------------- structured call ----
def test_call_traces_intent_request_response_and_understanding(repo, monkeypatch) -> None:
    root, _ = repo
    diag = Diagnosis(understanding="three tests failed on fct_x after the join changed",
                     root_cause="model_logic", summary="join fans out",
                     evidence="row count doubled", suggested_fix="dedupe", confidence="high",
                     escalate=False)
    fake = FakeParseClient(diag)
    base.set_client(fake)
    assert base.have_credentials()
    monkeypatch.setattr("pf.obs.record_agent_run", lambda **k: "id")

    with trace.start(root, "loop", "t", group="g", project="p") as tr:
        out = triage_failures(root, "g", "p",
                              [{"unique_id": "test.p.x", "status": "fail", "message": "m"}],
                              "model:fct_x -> model:dim_y")
    assert out is diag
    rows = trace.read(root, tr.id)
    by = {r["type"]: r for r in rows}
    assert by["intent"]["agent"] == "test_failure_triage"
    assert by["request"]["schema"] == "Diagnosis" and "test.p.x" in by["request"]["user"]
    assert by["request"]["system_sha256"] and "system" not in by["request"]["params"]
    assert by["response"]["parsed"]["root_cause"] == "model_logic"
    assert by["understanding"]["understanding"].startswith("three tests failed")
    # The fake saw the structured-output contract.
    assert fake.calls[0]["output_format"] is Diagnosis


# ----------------------------------------------------------- ask (live) ----
def test_ask_live_runs_the_tool_loop_and_traces_it(repo, monkeypatch) -> None:
    from pf.agents import ask as ask_mod

    root, pdir = repo
    (pdir / "transform" / "target").mkdir(parents=True)
    (pdir / "transform" / "target" / "semantic_manifest.json").write_text(json.dumps(
        {"metrics": [{"name": "revenue", "type": "simple", "label": "Revenue"}]}), encoding="utf-8")
    monkeypatch.setattr(ask_mod, "dimensions_for", lambda p, m: "metric_time__month")
    monkeypatch.setattr(ask_mod, "query",
                        lambda p, m, g=None, w="", limit=50:
                        (True, "metric_time__month  revenue\n2026-07-01  10\n",
                         [{"metric_time__month": "2026-07-01", "revenue": "10"}]))
    monkeypatch.setattr("pf.obs.record_agent_run", lambda **k: "id")
    fake = FakeToolClient([
        [{"name": "list_metrics", "input": {}}],
        [{"name": "get_dimensions", "input": {"metrics": ["revenue"]}}],
        [{"name": "query_metrics", "input": {"metrics": ["revenue"],
                                             "group_by": ["metric_time__month"]}}],
        [{"name": "final_answer", "input": {
            "understanding": "revenue trend by month",
            "plan": ["list", "dims", "query by month"],
            "answer": "Revenue was 10 in July.", "metrics": ["revenue"],
            "group_by": ["metric_time__month"], "covered": True}}],
    ])
    base.set_client(fake)

    res = ask_mod.ask(root, "g", "p", "what was revenue by month?")
    assert res.path == "live" and res.answer.covered and res.turns == 4
    assert res.rows == [{"metric_time__month": "2026-07-01", "revenue": "10"}]
    # Only the three governed tools were offered; never SQL.
    offered = {t["name"] for t in fake.calls[0]["tools"]}
    assert offered == {"list_metrics", "get_dimensions", "query_metrics", "final_answer"}

    run = trace.index(root)[-1]
    assert run["kind"] == "ask"
    rows = trace.read(root, run["run"])
    calls = [r["tool"] for r in rows if r["type"] == "tool_call"]
    assert calls == ["list_metrics", "get_dimensions", "query_metrics"]
    results = [r for r in rows if r["type"] == "tool_result"]
    assert "revenue (simple)" in results[0]["result"]
    assert any(r["type"] == "understanding" and "trend" in r["understanding"] for r in rows)
    assert rows[-2]["type"] == "answer" and rows[-2]["answer"]["metrics"] == ["revenue"]


def test_ask_live_stops_at_the_turn_limit(repo, monkeypatch) -> None:
    from pf.agents import ask as ask_mod

    root, _ = repo
    monkeypatch.setattr("pf.obs.record_agent_run", lambda **k: "id")
    base.set_client(FakeToolClient([[{"name": "list_metrics", "input": {}}]] * 20))
    res = ask_mod.ask(root, "g", "p", "loop forever")
    assert not res.answer.covered and res.turns == ask_mod.MAX_TURNS
    assert any("turn limit" in c for c in res.answer.caveats)


# ----------------------------------------------------- runner + proposal ----
def test_loop_run_trace_carries_findings_and_proposal_chain(repo) -> None:
    root, _ = repo
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=root, check=True)
    spec = LoopSpec(name="demo", description="demo loop", autonomy="L1", cadence="x",
                    token_budget=0)

    def body(run: LoopRun) -> list[str]:
        run.propose(actions.Proposal(loop="demo", title="t", rationale="r",
                                     files={"transform/models/fct_x.sql": "select 1\n"}))
        return ["a finding"]

    run = run_loop(spec, body, root=root, group="g", project="p")
    assert run.outcome == "proposed"
    rows = trace.read(root, trace.index(root)[-1]["run"])
    types = [r["type"] for r in rows]
    assert types[:3] == ["start", "intent", "step"]                # breaker first
    assert "finding" in types and "proposal" in types
    steps = [r["step"] for r in rows if r["type"] == "step"]
    assert steps == ["circuit_breaker", "body", "memory", "proposal", "gate", "record"]
    assert rows[-1]["outcome"] == "proposed"


# --------------------------------------------------------------- decisions ----
def test_governance_acts_always_leave_a_decision_trace(tmp_path: Path) -> None:
    """Promotions, reverts, memory edits and proposal resolutions are decisions;
    each writes its own `decision` trace even with no run open."""
    from pf.evals import gate as eval_gate
    from pf.loops import levels, memory

    spec = LoopSpec(name="d", description="x", autonomy="L1", cadence="c", token_budget=0)
    levels.set_level(tmp_path, spec, "p", "L2", actor="a", reason="test")
    levels.record_revert(tmp_path, spec, "g", "p", actor="a", note="broke")
    # repo-root discovery needs the platform/ + groups/ pair, as in a real checkout
    (tmp_path / "platform").mkdir()
    pdir = tmp_path / "groups" / "g" / "projects" / "p"
    pdir.mkdir(parents=True)
    e = memory.remember(pdir, loop="*", pattern="x*", note="n")
    memory.forget(pdir, e.id)

    kinds = [r["name"] for r in trace.index(tmp_path) if r["kind"] == "decision"]
    assert kinds == ["level:d", "revert:d", "level:d", "memory:remember", "memory:forget"]
    rows = trace.read(tmp_path, trace.index(tmp_path)[1]["run"])
    assert rows[1]["type"] == "decision" and rows[1]["note"] == "broke"
    assert eval_gate  # imported to keep the surface explicit in this test module
