"""Path gate.

The gate is the one rule that is enforced rather than remembered, so both of its
failure directions cost something real: a hole lets an agent write a credential
file, and a false positive makes an ordinary source file uneditable and teaches
everyone to reach for `--no-verify`. The cases below pin both.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import REPO_ROOT
from pf.loops.gate import _is_name_heuristic, check_path, check_paths

ROOT = REPO_ROOT

#: Paths that must stay denied. Each is a real thing the gate exists to stop.
MUST_DENY = [
    ".env",
    ".env.local",
    "groups/g/projects/p/.dlt/secrets.toml",
    "groups/g/projects/p/credentials/aws.txt",
    "groups/g/projects/p/api_key.pem",
    "groups/g/projects/p/private_key.json",
    "groups/g/projects/p/client_secret.toml",
    # Generated artefacts: denied for where they are, not what they are called,
    # so the heuristic guard must not reach them.
    "groups/g/projects/p/transform/target/compiled/some_key_model.sql",
    "groups/g/projects/p/transform/dbt_packages/dbt_utils/macros/x_key_y.sql",
    "groups/g/projects/p/kg/graph.duckdb",
    "groups/g/projects/p/data/p.duckdb",
]

#: Ordinary project files whose *names* trip a credential heuristic. Every one of
#: these is a real thing an analytics engineer writes.
MUST_ALLOW = [
    "groups/g/projects/p/transform/macros/surrogate_key_hash.sql",
    "groups/g/projects/p/transform/models/marts/dim_key_accounts.sql",
    "groups/g/projects/p/transform/models/staging/stg_secret_santa.sql",
    "groups/g/projects/p/decisions/ADR-0007-primary-key-strategy.md",
    "docs/secret-management.md",
]


@pytest.mark.parametrize("path", MUST_DENY)
def test_real_secrets_and_artefacts_stay_denied(path: str) -> None:
    assert check_path(path, ROOT).blocked, path


@pytest.mark.parametrize("path", MUST_ALLOW)
def test_source_files_are_not_denied_for_their_name(path: str) -> None:
    """`**/*_key*` is a guess from a filename. It denied `surrogate_key_hash.sql`
    — an ordinary dbt macro — and would have denied the next project's
    `dim_key_accounts.sql` too. A guess must not outrank the fact that a `.sql`
    file cannot hold a credential."""
    assert not check_path(path, ROOT).blocked, path


def test_the_guard_is_structural_not_a_list_of_exceptions() -> None:
    """A pattern whose basename is wrapped in `*` matches a substring of a name,
    which is what makes it a heuristic. Naming files is not."""
    assert _is_name_heuristic("**/*_key*")
    assert _is_name_heuristic("**/*_secret*")
    assert not _is_name_heuristic("**/secrets.toml")
    assert not _is_name_heuristic("**/credentials/**")
    assert not _is_name_heuristic("**/target/**")
    assert not _is_name_heuristic(".env.*")


def test_platform_paths_are_denied_only_inside_a_project_session() -> None:
    p = "platform/src/pf/cli.py"
    assert not check_path(p, ROOT).blocked
    assert check_path(p, ROOT, in_project=True).blocked


def test_impact_required_warns_rather_than_blocks(tmp_path: Path) -> None:
    """Changing a model is allowed; doing it without reporting the blast radius
    is what the gate wants to catch.

    Written against a policy of its own rather than the repository's, because
    the repository's `autoMergeAllowlist` currently contains `**/*.sql` and the
    allowlist is checked first — so no model file reaches this rule. That is a
    live contradiction between two sections of `gate.yaml` and a decision about
    workflow, not something a test should quietly assert away.
    """
    (tmp_path / "gate.yaml").write_text(
        "version: 1\nimpact_required:\n  - '**/transform/models/**/*.sql'\n", encoding="utf-8"
    )
    r = check_path("groups/g/projects/p/transform/models/marts/fct_x.sql", tmp_path)
    assert r.verdict == "warn"
    assert "impact" in r.message


def test_the_allowlist_outranks_impact_required(tmp_path: Path) -> None:
    """Pinning the precedence, because it is what makes the contradiction above
    invisible: a broad allowlist entry silently disables a narrow impact rule."""
    (tmp_path / "gate.yaml").write_text(
        "version: 1\nautoMergeAllowlist:\n  - '**/*.sql'\nimpact_required:\n  - '**/transform/models/**/*.sql'\n",
        encoding="utf-8",
    )
    assert check_path("g/p/transform/models/m.sql", tmp_path).verdict == "allow"


def test_env_example_is_the_one_documented_exception() -> None:
    """`.env.*` has to catch `.env.local`; it also caught the committed template
    that is the one file someone edits when adding a variable."""
    assert not check_path(".env.example", ROOT).blocked


def test_a_run_that_touches_too_many_files_is_blocked_as_a_whole(
    tmp_path: Path,
) -> None:
    (tmp_path / "gate.yaml").write_text("version: 1\nmaxFiles: 2\n", encoding="utf-8")
    results = check_paths([f"a/{i}.md" for i in range(3)], tmp_path)
    assert any(r.blocked and "maxFiles" in r.rule for r in results)


# ------------------------------------------- a change lands with its map -----
#
# `gate.yaml`'s `harness_required`: a run that changes a scope must leave that
# scope's HARNESS.md current. Judged on currency, not presence, so the cases pin
# both directions — a change that alters a map is refused without it, and a
# change that leaves the map identical costs nothing.
_HARNESS_RULE = """\
version: 1
harness_required:
  - scope: "groups/*/projects/*/**"
    maps:
      - "groups/{group}/projects/{project}/HARNESS.md"
      - "groups/{group}/projects/{project}/reporting/HARNESS.md"
      - "groups/{group}/HARNESS.md"
  - scope: "groups/*/**"
    maps:
      - "groups/{group}/**/HARNESS.md"
"""


def _scoped(tmp_path: Path) -> Path:
    """A group with one project, its maps current, and the rule declared."""
    from pf import harnessmap

    (tmp_path / "gate.yaml").write_text(_HARNESS_RULE, encoding="utf-8")
    (tmp_path / "groups" / "demo" / "projects" / "demo-us").mkdir(parents=True)
    harnessmap.write(tmp_path)
    return tmp_path


def _harness_denials(results) -> dict[str, str]:
    return {r.path: r.message for r in results if r.blocked and r.rule.startswith("harness_required")}


def test_a_change_that_alters_the_map_is_refused_without_it(tmp_path: Path) -> None:
    """An ADR changes the project's decisions count, so its map is stale; the message names the verb."""
    root = _scoped(tmp_path)
    changed = "groups/demo/projects/demo-us/decisions/ADR-0001-x.md"
    (root / changed).parent.mkdir()
    (root / changed).write_text("# x\n", encoding="utf-8")
    denied = _harness_denials(check_paths([changed], root))
    assert set(denied) == {"groups/demo/projects/demo-us/HARNESS.md"}, denied
    assert "pf harness demo demo-us" in denied["groups/demo/projects/demo-us/HARNESS.md"]
    assert changed in denied["groups/demo/projects/demo-us/HARNESS.md"]


def test_a_change_that_leaves_the_map_identical_needs_nothing(tmp_path: Path) -> None:
    """A staging model is not a fact the map states, so the run is not asked for the map."""
    root = _scoped(tmp_path)
    changed = "groups/demo/projects/demo-us/transform/models/staging/stg_x.sql"
    (root / changed).parent.mkdir(parents=True)
    (root / changed).write_text("select 1\n", encoding="utf-8")
    assert _harness_denials(check_paths([changed], root)) == {}


def test_the_regenerated_map_in_the_same_run_passes(tmp_path: Path) -> None:
    from pf import harnessmap

    root = _scoped(tmp_path)
    changed = "groups/demo/projects/demo-us/decisions/ADR-0001-x.md"
    (root / changed).parent.mkdir()
    (root / changed).write_text("# x\n", encoding="utf-8")
    harnessmap.write(root, "demo", "demo-us")
    run = [changed, "groups/demo/projects/demo-us/HARNESS.md"]
    assert _harness_denials(check_paths(run, root)) == {}


def test_a_group_level_change_reaches_every_map_in_the_family(tmp_path: Path) -> None:
    """Enabling a tool for the family changes the group's map and every sister's."""
    root = _scoped(tmp_path)
    changed = "groups/demo/tools.yaml"
    (root / changed).write_text("version: 1\ntools:\n  recce:\n    enabled: true\n", encoding="utf-8")
    denied = _harness_denials(check_paths([changed], root))
    assert set(denied) == {"groups/demo/HARNESS.md", "groups/demo/projects/demo-us/HARNESS.md"}, denied


def test_a_map_for_a_scope_that_does_not_exist_is_never_demanded(tmp_path: Path) -> None:
    """The project has no reporting/, so its report map is not a thing to be current."""
    root = _scoped(tmp_path)
    changed = "groups/demo/projects/demo-us/decisions/ADR-0001-x.md"
    (root / changed).parent.mkdir()
    (root / changed).write_text("# x\n", encoding="utf-8")
    assert not any("reporting" in p for p in _harness_denials(check_paths([changed], root)))


def test_a_map_regenerated_but_not_staged_is_refused(tmp_path: Path) -> None:
    """Current on disk is not enough: the commit would lack it. Needs a repository to tell."""
    import subprocess

    from pf import harnessmap

    root = _scoped(tmp_path)
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
    subprocess.run([*git, "init", "-q"], cwd=root, check=True)
    subprocess.run([*git, "add", "-A"], cwd=root, check=True)
    subprocess.run([*git, "commit", "-q", "-m", "maps"], cwd=root, check=True)
    changed = "groups/demo/projects/demo-us/decisions/ADR-0001-x.md"
    (root / changed).parent.mkdir()
    (root / changed).write_text("# x\n", encoding="utf-8")
    # Staged, as the pre-commit hook sees it: inside a repository the map counts
    # only what git holds, so an unstaged ADR would not change it at all.
    subprocess.run([*git, "add", changed], cwd=root, check=True)
    harnessmap.write(root, "demo", "demo-us")
    denied = _harness_denials(check_paths([changed], root))
    assert set(denied) == {"groups/demo/projects/demo-us/HARNESS.md"}
    assert "git add groups/demo/projects/demo-us/HARNESS.md" in denied["groups/demo/projects/demo-us/HARNESS.md"]
    run = [changed, "groups/demo/projects/demo-us/HARNESS.md"]
    assert _harness_denials(check_paths(run, root)) == {}


def test_paths_outside_every_scope_are_not_judged(tmp_path: Path) -> None:
    root = _scoped(tmp_path)
    assert _harness_denials(check_paths(["platform/src/pf/cli.py", "docs/x.md"], root)) == {}


def test_this_repository_names_the_rule_and_its_maps_are_current() -> None:
    """The rule is declared here, and the checkout it judges passes it for every scope."""
    from pf import harnessmap
    from pf.loops.gate import load_policy

    rules = load_policy(ROOT).get("harness_required") or []
    assert any(r.get("scope") == "groups/*/projects/*/**" for r in rules)
    assert [str(d) for d in harnessmap.drift(ROOT) if not d.ok] == []
