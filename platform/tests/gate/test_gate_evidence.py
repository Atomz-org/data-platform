"""A feature and its evidence land together — `gate.yaml`'s `tests_required`.

`pytest` and the contract evals say whether the suite is green. Nothing said
whether a change *has* a suite: a new module with no test, or a new skill with
no eval case, passed every check there was by having nothing to fail. This rule
closes that, and these pin the properties that make it a rule rather than a
nuisance:

  new is refused, changed     the cost of a missing test is highest on the day
    is warned                   the feature lands; on every later edit a hard
                                block would teach everyone to reach for
                                --no-verify

  evidence must share the     a skill in one toolkit is not covered by an eval
    scope                       in another; the pair is per toolkit

  a deleted test is not       the gate never sees deletions, so the one way a
    evidence                    rule like this is usually gamed is closed by
                                construction, and pinned here so it stays so

  unknown status is new       a caller that cannot say whether a file is new
                                gets the strict reading

What the gate cannot judge — whether the evidence is real, whether it failed
before the change — is review's to keep, and `AGENTS.md` §4 says so.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from conftest import REPO_ROOT
from pf.loops.gate import check_evidence, check_paths, load_policy

ROOT = REPO_ROOT

POLICY = """\
version: 1
tests_required:
  - source: "platform/src/pf/**/*.py"
    evidence: "platform/tests/**/*.py"
  - source: "platform/toolkits/*/skills/**"
    evidence: "platform/toolkits/*/evals/**"
    scope: 3
"""


def _root(tmp_path: Path) -> Path:
    (tmp_path / "gate.yaml").write_text(POLICY, encoding="utf-8")
    return tmp_path


def _rules(results) -> set[tuple[str, str]]:
    return {(r.verdict, r.path) for r in results if r.rule.startswith("tests_required")}


# ------------------------------------------------------------ the pairing --
def test_a_new_source_file_without_evidence_is_refused(tmp_path: Path) -> None:
    root = _root(tmp_path)
    src = "platform/src/pf/harness.py"
    [r] = check_evidence([src], root, added=[src])
    assert r.blocked
    assert r.rule == "tests_required:platform/src/pf/**/*.py"
    assert r.path == src, "the message names the file, not the rule"
    assert "platform/tests/**/*.py" in r.message


def test_a_modified_source_file_without_evidence_is_warned(tmp_path: Path) -> None:
    """A hard block on every later edit is how a rule teaches --no-verify."""
    root = _root(tmp_path)
    [r] = check_evidence(["platform/src/pf/harness.py"], root, added=[])
    assert r.verdict == "warn"
    assert "changed" in r.message


def test_evidence_in_the_same_run_satisfies_the_pair(tmp_path: Path) -> None:
    root = _root(tmp_path)
    paths = ["platform/src/pf/harness.py", "platform/tests/gate/test_harness.py"]
    assert check_evidence(paths, root, added=paths) == []


def test_evidence_that_is_not_a_test_file_does_not_count(tmp_path: Path) -> None:
    """The regenerated test index lives under platform/tests too. It is not a test."""
    root = _root(tmp_path)
    paths = ["platform/src/pf/harness.py", "platform/tests/README.md"]
    [r] = check_evidence(paths, root, added=["platform/src/pf/harness.py"])
    assert r.blocked


def test_unknown_status_is_judged_as_new(tmp_path: Path) -> None:
    root = _root(tmp_path)
    [r] = check_evidence(["platform/src/pf/harness.py"], root, added=None)
    assert r.blocked, "a caller that cannot say a file is not new gets the strict reading"


def test_paths_outside_every_pair_are_not_judged(tmp_path: Path) -> None:
    root = _root(tmp_path)
    assert check_evidence(["docs/HARNESSES.md", "groups/g/projects/p/x.sql"], root, added=None) == []


# ------------------------------------------------------------------ scope --
def test_evidence_must_share_the_scope(tmp_path: Path) -> None:
    """An eval in one toolkit does not cover a skill in another."""
    root = _root(tmp_path)
    skill = "platform/toolkits/dbt-govern/skills/triage/SKILL.md"
    wrong = "platform/toolkits/forge-ui/evals/cases/a.yaml"
    right = "platform/toolkits/dbt-govern/evals/cases/a.yaml"

    [r] = check_evidence([skill, wrong], root, added=[skill])
    assert r.blocked
    assert "platform/toolkits/dbt-govern" in r.message, "the message says which toolkit's evals"

    assert check_evidence([skill, right], root, added=[skill]) == []


def test_a_pair_without_scope_is_repository_wide(tmp_path: Path) -> None:
    root = _root(tmp_path)
    paths = ["platform/src/pf/loops/gate.py", "platform/tests/onboarding/test_x.py"]
    assert check_evidence(paths, root, added=paths) == []


# ---------------------------------------------------------------- wiring --
def test_check_paths_carries_the_verdict(tmp_path: Path) -> None:
    """`pf gate` reads `check_paths`; a rule that only `check_evidence` knows
    about is a rule nothing runs."""
    root = _root(tmp_path)
    src = "platform/src/pf/harness.py"
    assert ("deny", src) in _rules(check_paths([src], root, added=[src]))
    assert ("warn", src) in _rules(check_paths([src], root, added=[]))
    assert _rules(check_paths([src, "platform/tests/t.py"], root, added=[src])) == set()


def test_a_deleted_test_cannot_be_evidence() -> None:
    """The pre-commit hook selects ACMR and never D, so a removed test is not in
    the path list at all. Pinned by reading the hook: the day someone adds D
    to the filter, this is the test that asks whether deletions now count."""
    hook = (ROOT / "platform" / "hooks" / "pre_commit.sh").read_text(encoding="utf-8")
    assert "--diff-filter=ACMR" in hook
    assert "--diff-filter=A" in hook, "the hook must pass the added subset, or every edit is judged as new"
    assert "--added" in hook


# --------------------------------------------------------- this repository --
def test_this_repository_names_the_pairs() -> None:
    """The control is named, not asserted: `gate.yaml` carries the rule, with
    its reason beside it, and the three roots a feature can land in."""
    policy = load_policy(ROOT)
    pairs = policy.get("tests_required") or []
    sources = {p["source"] for p in pairs}
    assert "platform/src/pf/**/*.py" in sources
    assert "platform/hooks/**" in sources
    assert any(s.startswith("platform/toolkits/") and "skills" in s for s in sources)
    toolkit = next(p for p in pairs if "toolkits" in p["source"])
    assert toolkit.get("scope") == 3, "a skill is covered by its own toolkit's evals, not another's"

    text = (ROOT / "gate.yaml").read_text(encoding="utf-8")
    assert "A feature and its evidence land together" in text, "the reason lives beside the rule"


def test_the_pr_workflow_passes_file_status_too() -> None:
    """Enforced on the PR, not only on the developer's machine."""
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / "claude-review.yml").read_text(encoding="utf-8"))
    steps = [s for j in wf["jobs"].values() for s in j.get("steps", [])]
    gate_step = next(s for s in steps if "pf gate" in str(s.get("run", "")))
    assert "--added" in gate_step["run"]
    assert "--diff-filter=A" in gate_step["run"]


def test_this_change_satisfies_its_own_rule() -> None:
    """The rule applies to the commit that introduces it: the gate module
    changed, and this file is the evidence, in the same run."""
    paths = [
        "platform/src/pf/loops/gate.py",
        "platform/src/pf/cli.py",
        "platform/hooks/pre_commit.sh",
        "platform/tests/gate/test_gate_evidence.py",
    ]
    assert check_evidence(paths, ROOT, added=["platform/tests/gate/test_gate_evidence.py"]) == []
