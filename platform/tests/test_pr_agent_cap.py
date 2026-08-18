"""Who the `maxFiles` run cap applies to.

The cap was written to keep one agent run small, and `pf pr report` exempted
pull requests so that ordinary human PRs did not BLOCK for touching 20 files.
The exemption was too broad: an agent that opened a PR instead of committing in
a loop run inherited the human exemption, so the one case the cap existed for
was the case it stopped covering.

These pin both halves. A human PR must stay exempt — that is the regression the
original exemption was protecting against, and re-introducing it would be worse
than the gap. An agent PR must be capped.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pf.pr import agent_authored

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """The signals read the environment, so every test starts from none set."""
    for var in ("PF_PR_AGENT", "PF_PR_LABELS", "GITHUB_PR_LABELS",
                "PF_PR_BRANCH", "GITHUB_HEAD_REF"):
        monkeypatch.delenv(var, raising=False)


# ------------------------------------------------------------------ human ----

def test_ordinary_branch_is_not_agent_authored():
    """The regression guard: a human PR must not inherit the run cap."""
    is_agent, why = agent_authored(ROOT, branch="feat/add-orders-model")
    assert is_agent is False
    assert "no agent signal" in why


@pytest.mark.parametrize("branch", [
    "main", "feat/x", "fix(gate)--maxfiles", "release/1.2", "vendors/thing",
])
def test_human_branch_names_stay_exempt(branch):
    """`vendors/` must not match the `vendor/` prefix — prefixes, not substrings."""
    assert agent_authored(ROOT, branch=branch)[0] is False


# ------------------------------------------------------------------ agent ----

@pytest.mark.parametrize("branch,prefix", [
    ("loop/freshness-triage", "loop/"),
    ("agent/refactor", "agent/"),
    ("vendor/sync", "vendor/"),
    ("bot/dependabot-bump", "bot/"),
])
def test_agent_branch_prefixes_are_capped(branch, prefix):
    is_agent, why = agent_authored(ROOT, branch=branch)
    assert is_agent is True
    assert prefix in why


def test_label_marks_a_pr_as_agent_authored(monkeypatch):
    monkeypatch.setenv("PF_PR_LABELS", "needs-review,agent-run")
    is_agent, why = agent_authored(ROOT, branch="feat/x")
    assert is_agent is True
    assert "agent-run" in why


def test_labels_are_case_insensitive(monkeypatch):
    monkeypatch.setenv("PF_PR_LABELS", "Agent-Run")
    assert agent_authored(ROOT, branch="feat/x")[0] is True


def test_github_pr_labels_is_accepted_too(monkeypatch):
    monkeypatch.setenv("GITHUB_PR_LABELS", "loop")
    assert agent_authored(ROOT, branch="feat/x")[0] is True


# --------------------------------------------------------------- override ----

def test_explicit_override_forces_the_cap_on(monkeypatch):
    monkeypatch.setenv("PF_PR_AGENT", "1")
    is_agent, why = agent_authored(ROOT, branch="feat/x")
    assert is_agent is True
    assert "PF_PR_AGENT" in why


def test_explicit_override_forces_the_cap_off(monkeypatch):
    """The escape hatch, and it must beat every heuristic.

    A human landing a large reviewed change from a `loop/` branch needs a way
    out that is visible in a workflow file, rather than reaching for
    `--no-verify` where nobody sees it.
    """
    monkeypatch.setenv("PF_PR_AGENT", "0")
    is_agent, why = agent_authored(ROOT, branch="loop/anything")
    assert is_agent is False
    assert "explicitly disables" in why


def test_override_beats_a_matching_label(monkeypatch):
    monkeypatch.setenv("PF_PR_LABELS", "agent-run")
    monkeypatch.setenv("PF_PR_AGENT", "0")
    assert agent_authored(ROOT, branch="feat/x")[0] is False


# ----------------------------------------------------------------- policy ----

def test_signals_come_from_gate_yaml_not_from_code(tmp_path):
    """A repo whose gate.yaml declares no `agent_pr` block caps nothing.

    Pinned because the alternative — defaulting to a hardcoded prefix list when
    the policy is absent — would apply a cap the repo never asked for, and the
    first anyone would know is a PR blocking for a rule not in their gate.yaml.
    """
    (tmp_path / "gate.yaml").write_text("version: 1\nmaxFiles: 12\n")
    is_agent, why = agent_authored(tmp_path, branch="loop/x")
    assert is_agent is False
    assert "no `agent_pr` signals" in why


def test_the_repo_actually_declares_the_signals():
    """Guards the wiring: the block must exist here, or every test above is moot."""
    import yaml

    policy = yaml.safe_load((ROOT / "gate.yaml").read_text())
    assert "agent_pr" in policy, "gate.yaml lost its agent_pr block"
    assert policy["agent_pr"].get("branch_prefixes")
    assert policy.get("maxFiles"), "the cap this scopes no longer exists"


# --------------------------------------------------------------- CI shapes ----

def test_detached_head_in_ci_falls_back_to_the_pr_ref(monkeypatch):
    """Actions checks a PR out detached, so git reports "HEAD", not the branch.

    Without the fallback every `loop/` PR scores as human and the policy looks
    configured while enforcing nothing.
    """
    monkeypatch.setenv("GITHUB_HEAD_REF", "loop/nightly-triage")
    is_agent, why = agent_authored(ROOT, branch="HEAD")
    assert is_agent is True
    assert "loop/nightly-triage" in why


def test_explicit_pr_branch_beats_github_head_ref(monkeypatch):
    monkeypatch.setenv("GITHUB_HEAD_REF", "feat/x")
    monkeypatch.setenv("PF_PR_BRANCH", "vendor/sync")
    assert agent_authored(ROOT, branch="HEAD")[0] is True


def test_unknown_branch_does_not_crash_or_falsely_match(monkeypatch):
    monkeypatch.setenv("PF_PR_BRANCH", "")
    monkeypatch.setenv("GITHUB_HEAD_REF", "")
    assert agent_authored(ROOT, branch="HEAD")[0] is False
