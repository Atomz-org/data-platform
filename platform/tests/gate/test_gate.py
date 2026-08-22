"""Tests for the path gate.

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
        "version: 1\nimpact_required:\n  - '**/transform/models/**/*.sql'\n")
    r = check_path("groups/g/projects/p/transform/models/marts/fct_x.sql", tmp_path)
    assert r.verdict == "warn"
    assert "impact" in r.message


def test_the_allowlist_outranks_impact_required(tmp_path: Path) -> None:
    """Pinning the precedence, because it is what makes the contradiction above
    invisible: a broad allowlist entry silently disables a narrow impact rule."""
    (tmp_path / "gate.yaml").write_text(
        "version: 1\n"
        "autoMergeAllowlist:\n  - '**/*.sql'\n"
        "impact_required:\n  - '**/transform/models/**/*.sql'\n")
    assert check_path("g/p/transform/models/m.sql", tmp_path).verdict == "allow"


def test_env_example_is_the_one_documented_exception() -> None:
    """`.env.*` has to catch `.env.local`; it also caught the committed template
    that is the one file someone edits when adding a variable."""
    assert not check_path(".env.example", ROOT).blocked


def test_a_run_that_touches_too_many_files_is_blocked_as_a_whole(
    tmp_path: Path,
) -> None:
    (tmp_path / "gate.yaml").write_text("version: 1\nmaxFiles: 2\n")
    results = check_paths([f"a/{i}.md" for i in range(3)], tmp_path)
    assert any(r.blocked and "maxFiles" in r.rule for r in results)
