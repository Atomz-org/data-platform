"""Who the `maxFiles` run cap applies to.

The cap was written to keep one agent run small, and `pf pr report` exempted
pull requests so that ordinary human PRs did not BLOCK for touching 20 files.
The exemption was too broad: an agent that opened a PR instead of committing in
a loop run inherited the human exemption, so the one case the cap existed for
was the case it stopped covering.

These pin both halves. A human PR must stay exempt — that is the regression the
original exemption was protecting against, and re-introducing it would be worse
than the gap. An agent PR must be capped.

## Why almost everything here builds its own repo

An earlier version of this file asserted "a `feat/` branch is not agent work"
against *this* repository, and it passed — until a commit carrying
`Co-Authored-By: Claude` landed on the branch. Then the trailer signal matched,
every branch scored as agent work, and five branch tests failed for a reason
that had nothing to do with branches.

The tests were wrong, not the code: the answer genuinely depends on the commits
in range, so a test that wants to isolate one signal has to control the history
it runs against. Only `test_the_repo_actually_declares_the_signals` looks at the
real gate.yaml, and it asserts about policy rather than about a verdict.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pf.pr import agent_authored

ROOT = Path(__file__).resolve().parents[2]

FULL_POLICY = """\
version: 1
maxFiles: 12
agent_pr:
  labels: ["agent-run", "loop", "automated"]
  branch_prefixes: ["loop/", "agent/", "vendor/", "bot/"]
  trailers: ["Co-Authored-By: Claude", "Generated-By: pf-loop"]
"""


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Every signal reads the environment, so each test starts from none set."""
    for var in ("PF_PR_AGENT", "PF_PR_LABELS", "GITHUB_PR_LABELS",
                "PF_PR_BRANCH", "GITHUB_HEAD_REF"):
        monkeypatch.delenv(var, raising=False)


def _repo(tmp_path: Path, policy: str = FULL_POLICY, message: str = "work") -> Path:
    """A repo with a known policy and a known history.

    Two commits, so `base="HEAD~1"` names a real range. The PR commit's message
    is the caller's, which is what makes the trailer signal testable.
    """
    def git(*a: str) -> None:
        subprocess.run(["git", *a], cwd=tmp_path, check=True,
                       capture_output=True, text=True)

    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    (tmp_path / "gate.yaml").write_text(policy)
    git("add", "-A")
    git("commit", "-qm", "base")
    (tmp_path / "f.txt").write_text("x")
    git("add", "-A")
    git("commit", "-qm", message)
    return tmp_path


def _verdict(root: Path, **kw):
    return agent_authored(root, base="HEAD~1", **kw)


# ------------------------------------------------------------------ human ----

def test_ordinary_branch_is_not_agent_authored(tmp_path):
    """The regression guard: a human PR must not inherit the run cap."""
    is_agent, why = _verdict(_repo(tmp_path), branch="feat/add-orders-model")
    assert is_agent is False
    assert "no agent signal" in why


@pytest.mark.parametrize("branch", [
    "main", "feat/x", "fix(gate)--maxfiles", "release/1.2", "vendors/thing",
])
def test_human_branch_names_stay_exempt(tmp_path, branch):
    """`vendors/` must not match the `vendor/` prefix — prefixes, not substrings."""
    assert _verdict(_repo(tmp_path), branch=branch)[0] is False


# ------------------------------------------------------------------ agent ----

@pytest.mark.parametrize("branch,prefix", [
    ("loop/freshness-triage", "loop/"),
    ("agent/refactor", "agent/"),
    ("vendor/sync", "vendor/"),
    ("bot/dependabot-bump", "bot/"),
])
def test_agent_branch_prefixes_are_capped(tmp_path, branch, prefix):
    is_agent, why = _verdict(_repo(tmp_path), branch=branch)
    assert is_agent is True
    assert prefix in why


def test_label_marks_a_pr_as_agent_authored(tmp_path, monkeypatch):
    monkeypatch.setenv("PF_PR_LABELS", "needs-review,agent-run")
    is_agent, why = _verdict(_repo(tmp_path), branch="feat/x")
    assert is_agent is True
    assert "agent-run" in why


def test_labels_are_case_insensitive(tmp_path, monkeypatch):
    monkeypatch.setenv("PF_PR_LABELS", "Agent-Run")
    assert _verdict(_repo(tmp_path), branch="feat/x")[0] is True


def test_github_pr_labels_is_accepted_too(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_PR_LABELS", "loop")
    assert _verdict(_repo(tmp_path), branch="feat/x")[0] is True


# --------------------------------------------------------------- trailers ----

def test_trailer_in_the_pr_range_marks_it_agent_authored(tmp_path):
    """The signal this repo's own policy leans on hardest."""
    root = _repo(tmp_path, message="work\n\nCo-Authored-By: Claude Opus 5 <x@y>")
    is_agent, why = _verdict(root, branch="feat/x")
    assert is_agent is True
    assert "Co-Authored-By: Claude" in why


def test_a_non_matching_trailer_leaves_the_pr_human(tmp_path):
    root = _repo(tmp_path, message="work\n\nCo-Authored-By: a-colleague <x@y>")
    assert _verdict(root, branch="feat/x")[0] is False


def test_trailer_match_is_case_insensitive(tmp_path):
    root = _repo(tmp_path, message="work\n\nco-authored-by: CLAUDE opus 5 <x@y>")
    assert _verdict(root, branch="feat/x")[0] is True


def test_a_trailer_outside_the_pr_range_does_not_count(tmp_path):
    """One agent commit behind the branch point must not mark later PRs.

    Otherwise the first agent-authored commit to land on main would make every
    subsequent human PR agent-authored forever.
    """
    root = _repo(tmp_path, message="work\n\nCo-Authored-By: Claude Opus 5 <x@y>")
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "later human work"],
                   cwd=root, check=True, capture_output=True, text=True)
    # The PR is now only the last commit, which carries no trailer.
    assert agent_authored(root, base="HEAD~1", branch="feat/x")[0] is False


# --------------------------------------------------------------- override ----

def test_explicit_override_forces_the_cap_on(tmp_path, monkeypatch):
    monkeypatch.setenv("PF_PR_AGENT", "1")
    is_agent, why = _verdict(_repo(tmp_path), branch="feat/x")
    assert is_agent is True
    assert "PF_PR_AGENT" in why


def test_explicit_override_forces_the_cap_off(tmp_path, monkeypatch):
    """The escape hatch, and it must beat every heuristic.

    A human landing a large reviewed change from a `loop/` branch needs a way
    out that is visible in a workflow file, rather than reaching for
    `--no-verify` where nobody sees it.
    """
    monkeypatch.setenv("PF_PR_AGENT", "0")
    is_agent, why = _verdict(_repo(tmp_path), branch="loop/anything")
    assert is_agent is False
    assert "explicitly disables" in why


def test_override_beats_a_matching_label(tmp_path, monkeypatch):
    monkeypatch.setenv("PF_PR_LABELS", "agent-run")
    monkeypatch.setenv("PF_PR_AGENT", "0")
    assert _verdict(_repo(tmp_path), branch="feat/x")[0] is False


# ----------------------------------------------------------------- policy ----

def test_signals_come_from_gate_yaml_not_from_code(tmp_path):
    """A repo whose gate.yaml declares no `agent_pr` block caps nothing.

    Pinned because the alternative — defaulting to a hardcoded prefix list when
    the policy is absent — would apply a cap the repo never asked for, and the
    first anyone would know is a PR blocking for a rule not in their gate.yaml.
    """
    root = _repo(tmp_path, policy="version: 1\nmaxFiles: 12\n")
    is_agent, why = _verdict(root, branch="loop/x")
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

def test_detached_head_in_ci_falls_back_to_the_pr_ref(tmp_path, monkeypatch):
    """Actions checks a PR out detached, so git reports "HEAD", not the branch.

    Without the fallback every `loop/` PR scores as human and the policy looks
    configured while enforcing nothing.
    """
    monkeypatch.setenv("GITHUB_HEAD_REF", "loop/nightly-triage")
    is_agent, why = _verdict(_repo(tmp_path), branch="HEAD")
    assert is_agent is True
    assert "loop/nightly-triage" in why


def test_explicit_pr_branch_beats_github_head_ref(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_HEAD_REF", "feat/x")
    monkeypatch.setenv("PF_PR_BRANCH", "vendor/sync")
    assert _verdict(_repo(tmp_path), branch="HEAD")[0] is True


def test_unknown_branch_does_not_crash_or_falsely_match(tmp_path):
    assert _verdict(_repo(tmp_path), branch="HEAD")[0] is False
