"""Tests for the agentic layer: memory, the earned ladder, the action chain,
the eval gate, the funnel, and the seams that tie them to the runner.

Each of these is a place where the platform decides something on its own.
The cases pin the decisions that must not drift: a suppression needs a reason,
a promotion needs evidence, a proposal never merges, a revert always demotes,
an agent-surface change always runs the contract evals.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pf.evals import gate as eval_gate
from pf.loops import actions, levels, memory
from pf.loops.runner import Ledger, LoopRun, LoopSpec, run_loop
from pf.onboard.funnel import funnel


# ---------------------------------------------------------------- fixtures --
def _repo(tmp_path: Path, *, commit: bool = True) -> tuple[Path, Path]:
    """A platform-shaped git repo with one project."""
    root = tmp_path / "repo"
    pdir = root / "groups" / "g" / "projects" / "p"
    (root / "platform").mkdir(parents=True)
    (root / "groups" / "g" / "ontology").mkdir(parents=True)
    (pdir / "transform" / "models").mkdir(parents=True)
    (pdir / "transform" / "models" / "fct_x.sql").write_text("select 1 as x\n", encoding="utf-8")
    (root / "gate.yaml").write_text(
        "denylist:\n  - '**/.dlt/secrets.toml'\n  - '**/target/**'\n"
        "platform_denylist:\n  - 'platform/**'\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    if commit:
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=root, check=True)
    return root, pdir


def _spec(name: str = "test-loop", autonomy: str = "L1") -> LoopSpec:
    return LoopSpec(name=name, description="t", autonomy=autonomy, cadence="x",
                    token_budget=0)


def _row(loop: str, project: str, outcome: str, days_ago: float = 0) -> dict:
    at = datetime.now(UTC) - timedelta(days=days_ago)
    return LoopRun(run_id="r", loop=loop, group="g", project=project,
                   started_at=at.isoformat(timespec="seconds"), outcome=outcome).to_dict()


def _ledger(root: Path, rows: list[dict]) -> None:
    (root / "loop-ledger.json").write_text(json.dumps(rows), encoding="utf-8")


# ------------------------------------------------------------------ memory --
def test_memory_suppresses_and_annotates(tmp_path: Path) -> None:
    memory.remember(tmp_path, loop="freshness-triage", pattern="stg_stripe*",
                    note="late Mondays", expires="2999-01-01")
    memory.remember(tmp_path, loop="*", pattern="/PII column `dim_x/",
                    note="waiver #12", verb="annotate")
    out = memory.apply(tmp_path, "freshness-triage",
                       ["stg_stripe__charges.amount [freshness] warn",
                        "PII column `dim_x.email` reaches a mart",
                        "something else"])
    assert out.dropped == 1
    assert out.kept[0].endswith("[memory " + memory.load(tmp_path)[1].id + ": waiver #12]")
    assert out.kept[1] == "something else"
    # Hits are counted so audit can find entries that never fire.
    assert [e.hits for e in memory.load(tmp_path)] == [1, 1]


def test_memory_entry_scoped_to_its_loop(tmp_path: Path) -> None:
    memory.remember(tmp_path, loop="pii-audit", pattern="dim_x*", note="n")
    out = memory.apply(tmp_path, "freshness-triage", ["dim_x.email stale"])
    assert out.kept == ["dim_x.email stale"]


def test_memory_expired_entry_is_inert_and_audited(tmp_path: Path) -> None:
    memory.remember(tmp_path, loop="*", pattern="x*", note="n", expires="2000-01-01")
    assert memory.apply(tmp_path, "any", ["x1"]).kept == ["x1"]
    assert any("expired" in i for i in memory.audit(tmp_path))


def test_memory_refuses_entries_without_a_reason_or_with_unknown_keys(tmp_path: Path) -> None:
    p = memory.memory_path(tmp_path)
    p.parent.mkdir(parents=True)
    p.write_text("entries:\n  - pattern: x\n    loop: '*'\n", encoding="utf-8")
    with pytest.raises(memory.MemoryError):
        memory.load(tmp_path)
    p.write_text("entries:\n  - pattern: x\n    note: n\n    files: ['a']\n", encoding="utf-8")
    with pytest.raises(memory.MemoryError):
        memory.load(tmp_path)


def test_memory_audit_flags_open_ended_suppressions(tmp_path: Path) -> None:
    memory.remember(tmp_path, loop="*", pattern="x*", note="n")
    assert any("no expiry" in i for i in memory.audit(tmp_path))


# ------------------------------------------------------------------ levels --
def test_effective_level_defaults_to_birth(tmp_path: Path) -> None:
    assert levels.effective(tmp_path, _spec(autonomy="L2"), "p") == "L2"


def test_promotion_is_refused_without_evidence(tmp_path: Path) -> None:
    ev, rec = levels.promote(tmp_path, _spec(), "p", actor="a")
    assert rec is None and ev.target == "L2"
    assert any("clean runs" in b for b in ev.blockers)
    assert any("contract" in b for b in ev.blockers)


def test_promotion_on_evidence_then_revert_demotes(tmp_path: Path) -> None:
    spec = _spec()
    _ledger(tmp_path, [_row(spec.name, "p", "noop", days_ago=i) for i in range(25)])
    eval_gate.record(tmp_path, contract={"ok": True, "checks": 3, "failed": []})
    ev, rec = levels.promote(tmp_path, spec, "p", actor="a")
    assert ev.eligible and rec["level"] == "L2"
    assert levels.effective(tmp_path, spec, "p") == "L2"
    assert rec["reason"].startswith("earned")

    run, rec2 = levels.record_revert(tmp_path, spec, "g", "p", actor="h", note="broke a mart")
    assert run.outcome == "reverted"
    assert rec2["level"] == "L1"
    assert levels.effective(tmp_path, spec, "p") == "L1"
    # The clock resets: a revert counts as dirty in the recent window.
    ev2 = levels.eligibility(tmp_path, spec, "p")
    assert any("failure(s) in the last" in b for b in ev2.blockers)


def test_l3_needs_live_evals_and_no_reverts(tmp_path: Path) -> None:
    spec = _spec(autonomy="L2")
    _ledger(tmp_path, [_row(spec.name, "p", "ok", days_ago=i % 59) for i in range(60)])
    eval_gate.record(tmp_path, contract={"ok": True}, live={"ok": True, "pass_rate": 0.9})
    ev = levels.eligibility(tmp_path, spec, "p")
    assert ev.target == "L3"
    assert any("pass rate" in b for b in ev.blockers)
    eval_gate.record(tmp_path, live={"ok": True, "pass_rate": 0.97})
    assert levels.eligibility(tmp_path, spec, "p").eligible


def test_forced_promotion_is_recorded_as_forced(tmp_path: Path) -> None:
    _, rec = levels.promote(tmp_path, _spec(), "p", actor="boss", force=True)
    assert rec["level"] == "L2" and rec["reason"].startswith("forced")


def test_demote_never_goes_below_l1(tmp_path: Path) -> None:
    assert levels.demote(tmp_path, _spec(), "p", actor="a", reason="r") is None


# ----------------------------------------------------------------- actions --
def test_l1_proposal_is_recorded_only(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    p = actions.Proposal(loop="l", title="t", rationale="r",
                         files={"transform/models/fct_x.sql": "select 2 as x\n"})
    out = actions.execute(root, "g", "p", p, level="L1")
    assert out.status == "recorded" and not out.branch
    assert (root / "data" / "proposals" / f"{p.id}.json").exists()
    assert not (root / ".worktrees").exists()
    # Nothing touched the working tree.
    assert (root / "groups/g/projects/p/transform/models/fct_x.sql").read_text(encoding="utf-8") == "select 1 as x\n"


def test_gate_blocks_a_proposal_at_every_level(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    p = actions.Proposal(loop="l", title="t", rationale="r",
                         files={".dlt/secrets.toml": "key = 'x'"})
    out = actions.execute(root, "g", "p", p, level="L2")
    assert out.status == "gate_blocked"
    assert "denylist" in out.message
    assert subprocess.run(["git", "branch", "--list", "loop/*"], cwd=root,
                          capture_output=True, text=True).stdout.strip() == ""


def test_l2_proposal_branches_commits_and_never_merges(tmp_path: Path) -> None:
    root, pdir = _repo(tmp_path)
    p = actions.Proposal(loop="l", title="Fix x", rationale="because",
                         files={"transform/models/fct_x.sql": "select 2 as x\n"})
    out = actions.execute(root, "g", "p", p, level="L2", open_pr=False, run_review=False)
    assert out.status == "branched", out.message
    assert out.branch == f"loop/l/{p.id}" and out.commit
    # The branch carries the change; main does not; the worktree is gone.
    show = subprocess.run(["git", "show", f"{out.branch}:groups/g/projects/p/transform/models/fct_x.sql"],
                          cwd=root, capture_output=True, text=True).stdout
    assert show == "select 2 as x\n"
    assert (pdir / "transform/models/fct_x.sql").read_text(encoding="utf-8") == "select 1 as x\n"
    assert not (root / ".worktrees" / p.id).exists()
    head = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root,
                          capture_output=True, text=True).stdout.strip()
    assert head == "main"
    assert "left for review" in out.message


def test_mark_records_a_human_resolution(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    p = actions.Proposal(loop="l", title="t", rationale="r", files={"a.md": "x"})
    actions.execute(root, "g", "p", p, level="L1")
    assert actions.mark(root, p.id, "accepted", actor="h", note="merged")
    doc = actions.load_all(root)[0]
    assert doc["resolution"]["status"] == "accepted"
    assert not actions.mark(root, "nope", "accepted", actor="h")


# ------------------------------------------------------------------ runner --
def test_runner_executes_proposals_at_the_earned_level(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    spec = _spec()

    def body(run: LoopRun) -> list[str]:
        run.propose(actions.Proposal(loop=spec.name, title="t", rationale="r",
                                     files={"transform/models/fct_x.sql": "select 3\n"}))
        return ["found something"]

    run = run_loop(spec, body, root=root, group="g", project="p")
    assert run.outcome == "proposed" and run.level == "L1"
    assert run.proposals[0]["status"] == "recorded"
    assert Ledger(root).recent(spec.name, "p")[-1]["outcome"] == "proposed"


def test_runner_applies_memory_before_the_ledger(tmp_path: Path) -> None:
    root, pdir = _repo(tmp_path)
    memory.remember(pdir, loop="*", pattern="known*", note="accepted", expires="2999-01-01")
    run = run_loop(_spec(), lambda r: ["known thing", "new thing"],
                   root=root, group="g", project="p")
    assert run.findings == ["new thing"]
    assert run.suppressed == ["known thing"]
    assert Ledger(root).recent("test-loop", "p")[-1]["findings"] == ["new thing"]


def test_runner_reports_noop_when_memory_suppresses_everything(tmp_path: Path) -> None:
    root, pdir = _repo(tmp_path)
    memory.remember(pdir, loop="*", pattern="*", note="all known", expires="2999-01-01")
    run = run_loop(_spec(), lambda r: ["a", "b"], root=root, group="g", project="p")
    assert run.outcome == "noop" and run.suppressed == ["a", "b"]


# --------------------------------------------------------------- eval gate --
def test_agent_surface_is_explicit() -> None:
    hits = eval_gate.touches_agent_surface([
        "platform/src/pf/agents/loops.py", "platform/toolkits/dbt-govern/SKILL.md",
        "platform/toolkits/dbt-govern/skills/triage/SKILL.md", ".gitmodules",
        "groups/acme/projects/acme-eu/transform/models/x.sql",
        "platform/src/pf/kg/build.py",
    ])
    assert hits == ["platform/src/pf/agents/loops.py",
                    "platform/toolkits/dbt-govern/SKILL.md",
                    "platform/toolkits/dbt-govern/skills/triage/SKILL.md", ".gitmodules"]
    assert eval_gate.needs_live(["platform/src/pf/agents/loops.py", ".gitmodules"]) == \
        ["platform/src/pf/agents/loops.py"]


def test_every_prompt_module_is_on_the_surface() -> None:
    """A new prompt file that is not gated is the failure this pins."""
    root = Path(__file__).resolve().parents[2]
    for f in (root / "platform/src/pf/agents").glob("*.py"):
        rel = f.relative_to(root).as_posix()
        assert eval_gate.touches_agent_surface([rel]) == [rel]


def test_gate_report_logic() -> None:
    rep = eval_gate.GateReport(changed=["x"])
    assert rep.ok and not rep.required
    rep.surface = ["platform/src/pf/agents/base.py"]
    rep.contract_ok = True
    assert rep.ok
    rep.live_required = ["platform/src/pf/agents/base.py"]
    assert not rep.ok                      # live required, not run
    rep.live_ran, rep.live_ok = True, False
    assert not rep.ok
    rep.live_ok = True
    assert rep.ok
    rep.contract_ok = False
    assert not rep.ok


def test_run_gate_skips_when_nothing_on_the_surface_changed(tmp_path: Path) -> None:
    rep = eval_gate.run_gate(tmp_path, "", "", changed=["groups/g/projects/p/a.sql"])
    assert not rep.required and rep.skipped_reason
    assert not eval_gate.latest_path(tmp_path).exists()


def test_record_merges_tiers(tmp_path: Path) -> None:
    eval_gate.record(tmp_path, contract={"ok": True})
    eval_gate.record(tmp_path, live={"ok": False, "pass_rate": 0.5})
    doc = json.loads(eval_gate.latest_path(tmp_path).read_text(encoding="utf-8"))
    assert doc["contract"]["ok"] and doc["live"]["pass_rate"] == 0.5 and doc["live"]["at"]


# ------------------------------------------------------------------ funnel --
def test_funnel_reads_time_to_first_governed_metric(tmp_path: Path) -> None:
    _ledger(tmp_path, [
        _row("onboard-import", "p", "escalated", days_ago=3),
        _row("onboard-import", "p", "ok", days_ago=2.9),
        _row("onboard-ontology", "p", "ok", days_ago=2),
        _row("onboard-metrics", "p", "escalated", days_ago=1.5),
        _row("onboard-metrics", "p", "ok", days_ago=1),
    ])
    f = funnel(tmp_path, "g", "p")
    assert f.current == "dialect"
    assert f.stages[0].attempts == 2 and f.stages[0].passed
    assert f.hours_to_first_governed_metric == pytest.approx(48, abs=0.2)
    assert funnel(tmp_path, "g", "other").hours_to_first_governed_metric is None


# ----------------------------------------------------------------- the seam --
def test_evidence_is_a_tool_and_contributes_its_loop() -> None:
    from pf.loops.registry import all_specs
    from pf.tools import all_tools

    t = all_tools()["evidence"]
    assert t.capability is not None and t.capability.name == "evidence"
    assert t.loops and "dashboard-coverage" in all_specs()
    assert set(t.gate_sections()) <= {"denylist", "platform_denylist", "impact_required"}


def test_evidence_health_wants_node_20(monkeypatch: pytest.MonkeyPatch) -> None:
    from pf.tools import evidence

    monkeypatch.setattr(evidence, "node_version", lambda: (24, 1, 0))
    assert not evidence.health()["ok"]
    monkeypatch.setattr(evidence, "node_version", lambda: (20, 11, 0))
    assert evidence.health()["ok"]


def test_new_agents_are_routed_and_valid() -> None:
    from pf.agents.base import AGENTS, validate_routing

    assert {"fix_drafter", "metric_answerer"} <= set(AGENTS)
    assert not [i for i in validate_routing() if "unknown" in i.lower()]


# --------------------------------------------------------------------- ask --
def test_direct_answer_refuses_honestly_without_metrics(tmp_path: Path) -> None:
    from pf.agents.ask import answer_direct

    res = answer_direct(tmp_path, "revenue by month")
    assert not res.answer.covered and res.path == "direct"
    assert "no metrics defined" in res.answer.answer


def test_parse_table() -> None:
    from pf.agents.ask import _parse_table

    rows = _parse_table("metric_time__month  revenue\n------  ------\n2026-01-01  10.5\n2026-02-01  12\n")
    assert rows == [{"metric_time__month": "2026-01-01", "revenue": "10.5"},
                    {"metric_time__month": "2026-02-01", "revenue": "12"}]


# ------------------------------------------------------------------ notify --
def test_notify_without_a_webhook_is_a_clean_no(tmp_path: Path) -> None:
    from pf import notify

    ok, detail = notify.notify(tmp_path, "g", "hello")
    assert not ok and "no webhook" in detail


def test_render_run_mentions_proposals() -> None:
    from pf import notify

    run = LoopRun(run_id="r", loop="l", group="g", project="p", started_at="t",
                  outcome="proposed", findings=["f"], level="L2",
                  proposals=[{"proposal_id": "abc", "status": "proposed",
                              "pr_url": "https://x/pr/1"}])
    text = notify.render_run(run)
    assert "abc" in text and "https://x/pr/1" in text and "L2" in text
