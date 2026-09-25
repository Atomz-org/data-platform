"""Generated context is healed by CI, never a reason a pull request goes red.

One new test file used to turn four checks red: `agent-context` and
`platform-tests` each ran `pf test check`, and the suite that `platform` and
`platform-tests` both run held currency tests over the same files. Every one
of those files is rewritten by `pf context refresh`, so the workflows now
regenerate first and judge the result, `heal-main` commits whatever moved to
main after every merge, and the PR bot's push is optional. These pin that
shape, so a later edit cannot quietly bring the four red checks back — and
they pin the one script both healers commit through.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml
from conftest import REPO_ROOT
from pf.scaffold.bootstrap import PLATFORM_WORKFLOW

WORKFLOWS = REPO_ROOT / ".github" / "workflows"
SCRIPT = REPO_ROOT / "platform" / "hooks" / "commit_refreshed.sh"

#: A step that judges generated files: a drift check, or the suite that holds
#: currency tests over them.
_JUDGES = (
    "pytest platform/tests",
    "pf test check",
    "pf memory check",
    "pf arch check",
    "pf guide check",
    "pf harness check",
    "pf semantic mdl --check",
    "pf tool okf check",
)


def _steps(doc: dict, job: str) -> list[str]:
    return [str(s.get("run", "")) for s in doc["jobs"][job]["steps"]]


def _regenerates_before_judging(runs: list[str]) -> tuple[int | None, int | None]:
    regen = next((i for i, r in enumerate(runs) if "pf context refresh" in r and "--dry-run" not in r), None)
    judge = next((i for i, r in enumerate(runs) if any(j in r for j in _JUDGES)), None)
    return regen, judge


def test_every_job_that_judges_generated_files_regenerates_them_first() -> None:
    """A stale index is a warning in each of these, not a red check — the refresh precedes every judge."""
    jobs = {
        "agent-context/check": _steps(yaml.safe_load((WORKFLOWS / "agent-context.yml").read_text()), "check"),
        "platform-tests/suite": _steps(yaml.safe_load((WORKFLOWS / "platform-tests.yml").read_text()), "suite"),
        "platform/tests (template)": _steps(yaml.safe_load(PLATFORM_WORKFLOW), "tests"),
        "platform/tests (committed)": _steps(yaml.safe_load((WORKFLOWS / "platform.yml").read_text()), "tests"),
    }
    for name, runs in jobs.items():
        regen, judge = _regenerates_before_judging(runs)
        assert judge is not None, f"{name} judges nothing — the guard is looking at the wrong job"
        assert regen is not None and regen < judge, f"{name} must run `pf context refresh` before it judges"


def test_the_same_staleness_is_checked_in_one_workflow_only() -> None:
    """`agent-context` runs on every PR; `platform-tests` repeating its drift checks only doubled the red."""
    runs = _steps(yaml.safe_load((WORKFLOWS / "platform-tests.yml").read_text()), "suite")
    for dup in ("pf test check", "pf memory check", "pf arch check"):
        assert not any(dup in r for r in runs), f"platform-tests repeats `{dup}`; agent-context owns it"


def test_main_heals_itself_after_every_merge_with_no_personal_token() -> None:
    """The guarantee: main is regenerated on every push to it, with the workflow's own token."""
    doc = yaml.safe_load((WORKFLOWS / "agent-context.yml").read_text())
    job = doc["jobs"]["heal-main"]
    assert "refs/heads/main" in job["if"] and "push" in job["if"]
    assert job["permissions"] == {"contents": "write"}
    checkout = next(s for s in job["steps"] if str(s.get("uses", "")).startswith("actions/checkout"))
    assert "token" not in (checkout.get("with") or {}), "a personal token here would re-trigger workflows from main"
    script = "\n".join(_steps(doc, "heal-main"))
    assert "commit_refreshed.sh" in script and "git push origin HEAD:main" in script
    assert "git reset -q --hard origin/main" in script, "a lost race restarts from the new tip, never rebases"


def test_a_refresh_that_cannot_push_is_a_warning_not_a_red_check() -> None:
    doc = yaml.safe_load((WORKFLOWS / "agent-context.yml").read_text())
    job = doc["jobs"]["refresh"]
    assert "needs.check.outputs.stale == 'true'" in job["if"] and "always()" in job["if"]
    assert "if ! git push" in "\n".join(_steps(doc, "refresh"))


# ------------------------------------------------ the commit script ---------


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "t")
    _git(repo, "config", "user.email", "t@t")
    (repo / "keep.txt").write_text("k")
    (repo / "gone.md").write_text("g")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    return repo


def _commit(repo: Path, listed: list[str], cap: int) -> str:
    paths = repo.parent / "paths.txt"
    paths.write_text("".join(f"{p}\n" for p in listed))
    return subprocess.run(
        ["bash", str(SCRIPT), str(paths), str(cap), "Heal"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def test_the_script_commits_only_what_was_listed_within_the_cap_maps_first(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    listed = [f"docs/f{i:02}.md" for i in range(25)] + ["groups/g/HARNESS.md", "gone.md"]
    for p in listed[:-1]:
        (repo / p).parent.mkdir(parents=True, exist_ok=True)
        (repo / p).write_text("x")
    (repo / "gone.md").unlink()
    (repo / "keep.txt").write_text("an unrelated edit that must not ride along")

    assert _commit(repo, listed, cap=12) == "3"

    shas = _git(repo, "rev-list", "--reverse", "HEAD~3..HEAD").split()
    sizes = [len(_git(repo, "show", "--name-only", "--format=", s).split()) for s in shas]
    assert sizes == [12, 12, 3]
    first = _git(repo, "show", "--name-only", "--format=", shas[0]).split()
    assert "groups/g/HARNESS.md" in first, "harness maps go in the first commit"
    assert "gone.md" in _git(repo, "log", "--diff-filter=D", "--name-only", "--format=", "HEAD~3..HEAD")
    assert _git(repo, "status", "--porcelain").strip() == "M keep.txt", "only listed paths are committed"


def test_the_script_makes_no_commit_for_nothing(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    head = _git(repo, "rev-parse", "HEAD")
    assert _commit(repo, [], cap=12) == "0"
    assert _git(repo, "rev-parse", "HEAD") == head
