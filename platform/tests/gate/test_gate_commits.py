"""The file cap, re-applied to commits that already exist.

`maxFiles` was a per-*run* rule with exactly one caller: the pre-commit hook,
over one staged set. Both ordinary ways of skipping that hook leave nothing
behind. `git commit --no-verify` leaves no trace in the commit. A clone where
nobody has run `pf` has no hook to skip at all, because git does not clone
`.git/hooks` — which is how the only code path that enforced the cap went
uninvoked for the life of this repo while the policy read as configured.

So the number is measured twice more: on the way out of the machine, and again
over the commits a pull request adds. These pin what "the same rule" has to
mean for that to be honest rather than a second, differently-shaped rule —
the same `ACMR` file list the hook would have counted, per commit and never
over a union, merges left to the commits inside them — and the one way an
over-cap commit is still allowed: by saying in its own message why.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from conftest import REPO_ROOT
from pf.loops.gate import EXEMPT_TRAILER, GitError, check_commits, commit_files


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(root), check=True, capture_output=True, text=True
    ).stdout.strip()


def _repo(tmp_path: Path, cap: int = 2) -> Path:
    """A checkout with a policy and one commit to measure ranges against."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "gate@example.com")
    _git(tmp_path, "config", "user.name", "gate")
    (tmp_path / "gate.yaml").write_text(f"version: 1\nmaxFiles: {cap}\n", encoding="utf-8")
    _git(tmp_path, "add", "gate.yaml")
    _git(tmp_path, "commit", "-qm", "policy")
    return tmp_path


def _commit(root: Path, subject: str, names: list[str], *, trailer: str = "", args: tuple[str, ...] = ()) -> str:
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", subject if not trailer else f"{subject}\n\n{trailer}", *args)
    return _git(root, "rev-parse", "HEAD")


# ------------------------------------------------------------- the measure --

def test_a_commit_within_the_cap_is_not_reported(tmp_path: Path) -> None:
    root = _repo(tmp_path, cap=3)
    _commit(root, "small", ["a.txt", "b.txt"])
    assert check_commits(root, ["main~1..main"]) == []


def test_an_over_cap_commit_is_denied_and_named(tmp_path: Path) -> None:
    root = _repo(tmp_path, cap=2)
    sha = _commit(root, "too much at once", ["a.txt", "b.txt", "c.txt"])

    results = check_commits(root, ["main~1..main"])
    assert len(results) == 1
    assert results[0].blocked
    assert results[0].rule == "maxFiles:2"
    # The commit, not just a count: the author has to be able to find it.
    assert sha[:12] in results[0].path
    assert "too much at once" in results[0].path
    assert "3 files" in results[0].message


def test_the_commit_the_hook_never_saw_is_measured_anyway(tmp_path: Path) -> None:
    """`--no-verify` is the bypass this exists for.

    The hook here refuses everything, so the commit can only exist because it
    was skipped — and the whole point is that the commit itself records no sign
    of that. This is the check that notices afterwards.
    """
    root = _repo(tmp_path, cap=2)
    hook = root / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)

    with pytest.raises(subprocess.CalledProcessError):
        _commit(root, "blocked", ["a.txt", "b.txt", "c.txt"])
    _commit(root, "pushed past the gate", ["a.txt", "b.txt", "c.txt"], args=("--no-verify",))

    results = check_commits(root, ["main~1..main"])
    assert [r.verdict for r in results] == ["deny"]


def test_the_first_commit_in_a_repository_is_measured(tmp_path: Path) -> None:
    """A commit with no parent is still a commit. `--root`, or it is skipped."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "gate@example.com")
    _git(tmp_path, "config", "user.name", "gate")
    (tmp_path / "gate.yaml").write_text("version: 1\nmaxFiles: 2\n", encoding="utf-8")
    _commit(tmp_path, "everything at once", ["a.txt", "b.txt", "c.txt"])

    assert [r.verdict for r in check_commits(tmp_path, ["main"])] == ["deny"]


def test_no_cap_in_the_policy_judges_nothing(tmp_path: Path) -> None:
    root = _repo(tmp_path, cap=2)
    (root / "gate.yaml").write_text("version: 1\n", encoding="utf-8")
    _commit(root, "large", ["a.txt", "b.txt", "c.txt", "d.txt"])
    assert check_commits(root, ["main~1..main"]) == []


# ------------------------------------------------ the same list as the hook --

def test_deletions_do_not_count_the_way_the_hook_does_not_count_them(tmp_path: Path) -> None:
    """`--diff-filter=ACMR`, for the reason gate.yaml gives: removing a file is
    not editing one, and widening the gate to deletions is a policy change
    rather than something a re-check should decide on its own."""
    root = _repo(tmp_path, cap=2)
    _commit(root, "seed", ["a.txt"])
    _commit(root, "seed two", ["b.txt"])
    _commit(root, "seed three", ["c.txt"])
    for name in ("a.txt", "b.txt", "c.txt"):
        (root / name).unlink()
    (root / "d.txt").write_text("d", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "remove three, add one")

    assert commit_files(root, "HEAD") == ["d.txt"]
    assert check_commits(root, ["main~1..main"]) == []


def test_a_rename_counts_once_at_its_destination(tmp_path: Path) -> None:
    """`R` was missing from the filter once, and `git mv` was free of the gate."""
    root = _repo(tmp_path, cap=2)
    _commit(root, "seed", ["a.txt", "b.txt"])
    _git(root, "mv", "a.txt", "moved.txt")
    _git(root, "commit", "-qm", "move it")

    assert commit_files(root, "HEAD") == ["moved.txt"]


# ---------------------------------------------------------------- a merge ----

def test_a_merge_is_judged_by_its_parts_and_not_by_its_diff(tmp_path: Path) -> None:
    """A merge's first-parent diff is every file the branch ever touched.

    Capping that would refuse every merge while saying nothing about what is
    inside it. The commits inside it are each selected in their own right.
    """
    root = _repo(tmp_path, cap=2)
    _git(root, "checkout", "-q", "-b", "side")
    over = _commit(root, "side went wide", ["a.txt", "b.txt", "c.txt"])
    _git(root, "checkout", "-q", "main")
    _commit(root, "main moved on", ["m.txt"])
    _git(root, "merge", "-q", "--no-ff", "-m", "merge side", "side")

    results = check_commits(root, ["main"])
    assert [r.path.split()[0] for r in results] == [over[:12]]


# ------------------------------------------------------------- the reason ----

def test_a_commit_that_says_why_it_is_large_warns_instead_of_denying(tmp_path: Path) -> None:
    """The rule is not that a change may never exceed the cap. It is that
    exceeding it is never silent — which is exactly what `--no-verify` and a
    missing hook made it."""
    root = _repo(tmp_path, cap=2)
    _commit(
        root,
        "regenerate every bundle",
        ["a.txt", "b.txt", "c.txt"],
        trailer=f"{EXEMPT_TRAILER}: one `pf tool okf build`; splitting it commits a half-built bundle",
    )

    results = check_commits(root, ["main~1..main"])
    assert [r.verdict for r in results] == ["warn"]
    assert not results[0].blocked
    # The reason travels into the log and the review, or it is not a reason.
    assert "half-built bundle" in results[0].message


def test_a_trailer_with_no_reason_exempts_nothing(tmp_path: Path) -> None:
    root = _repo(tmp_path, cap=2)
    _commit(root, "large", ["a.txt", "b.txt", "c.txt"], trailer=f"{EXEMPT_TRAILER}:")
    assert [r.verdict for r in check_commits(root, ["main~1..main"])] == ["deny"]


def test_the_trailer_is_read_out_of_the_message_body_not_the_subject(tmp_path: Path) -> None:
    """A subject line mentioning the trailer is prose, not an exemption."""
    root = _repo(tmp_path, cap=2)
    _commit(root, f"about the {EXEMPT_TRAILER} rule", ["a.txt", "b.txt", "c.txt"])
    assert [r.verdict for r in check_commits(root, ["main~1..main"])] == ["deny"]


# ---------------------------------------------------------- failing loudly ----

def test_a_range_that_does_not_resolve_raises_rather_than_passing(tmp_path: Path) -> None:
    """The failure mode that would undo the whole check.

    An unfetched base or a shallow clone selects no commits, which reads
    exactly like a branch where every commit is within the cap. Silence has to
    mean "measured and fine", never "could not measure".
    """
    root = _repo(tmp_path, cap=2)
    with pytest.raises(GitError):
        check_commits(root, ["origin/nowhere..HEAD"])


# ------------------------------------------------------------- it is wired ----

def test_this_repository_runs_the_check_on_every_pull_request() -> None:
    """The control this repo keeps rediscovering: written, and wired to nothing.

    `pf tokens`, `pf check` and `pf loop audit` were each enforcing and
    unreferenced; `maxFiles` itself was enforced only by a hook nobody had
    installed. A re-check that no workflow calls is the same failure again, so
    the wiring is the assertion.
    """
    import yaml
    from pf.loops.gate import load_policy

    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/agent-context.yml").read_text(encoding="utf-8"))

    # Every pull request, not only ones touching platform paths.
    assert "pull_request" in (workflow.get(True) or workflow.get("on"))

    check = workflow["jobs"]["check"]
    steps = check["steps"]
    capped = [s for s in steps if "--commits" in str(s.get("run", ""))]
    assert len(capped) == 1, "no step re-applies the per-commit file cap"

    # Against the base branch, and with the history to resolve it: a shallow
    # checkout cannot see the commits it is meant to be measuring.
    assert "base.ref" in capped[0]["run"]
    checkout = next(s for s in steps if str(s.get("uses", "")).startswith("actions/checkout"))
    assert checkout["with"]["fetch-depth"] == 0

    # And the number it applies is this repository's, not a copy.
    assert int(load_policy(REPO_ROOT).get("maxFiles") or 0) > 0


def test_this_branch_is_within_the_cap_commit_by_commit() -> None:
    """The check, run against the history that introduced it."""
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), capture_output=True, text=True, check=False
    )
    if head.returncode != 0:
        pytest.skip("not a git checkout")
    base = subprocess.run(
        ["git", "merge-base", "HEAD", "origin/main"], cwd=str(REPO_ROOT), capture_output=True, text=True, check=False
    )
    if base.returncode != 0:
        pytest.skip("no origin/main to measure against")

    denied = [r for r in check_commits(REPO_ROOT, [f"{base.stdout.strip()}..HEAD"]) if r.blocked]
    assert denied == [], "\n".join(f"{r.path}: {r.message}" for r in denied)


# ------------------------------------------------------------ the command ----

def _invoke(root: Path, spec: str, monkeypatch):
    from pf import cli
    from typer.testing import CliRunner

    monkeypatch.setenv("PF_NO_HOOK_INSTALL", "1")
    monkeypatch.setattr(cli, "root", lambda: root)
    return CliRunner().invoke(cli.app, ["gate", "--commits", spec])


def test_the_command_exits_non_zero_so_a_hook_and_a_workflow_both_stop(tmp_path, monkeypatch) -> None:
    root = _repo(tmp_path, cap=2)
    _commit(root, "large", ["a.txt", "b.txt", "c.txt"])

    res = _invoke(root, "main~1..main", monkeypatch)
    assert res.exit_code == 1, res.output
    assert "DENY" in res.output


def test_an_exempt_commit_passes_and_the_summary_does_not_contradict_it(tmp_path, monkeypatch) -> None:
    root = _repo(tmp_path, cap=2)
    _commit(root, "large", ["a.txt", "b.txt", "c.txt"], trailer=f"{EXEMPT_TRAILER}: one regeneration")

    res = _invoke(root, "main~1..main", monkeypatch)
    assert res.exit_code == 0, res.output
    assert "WARN" in res.output
    # It is over the cap and passing; a line claiming otherwise is a lie the
    # reader has to reconcile against the warning above it.
    assert "without a reason" in " ".join(res.output.split())


def test_neither_flag_is_refused_rather_than_read_as_nothing_to_check(tmp_path, monkeypatch) -> None:
    from pf import cli
    from typer.testing import CliRunner

    monkeypatch.setenv("PF_NO_HOOK_INSTALL", "1")
    monkeypatch.setattr(cli, "root", lambda: _repo(tmp_path))
    assert CliRunner().invoke(cli.app, ["gate"]).exit_code == 2
