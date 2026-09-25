"""Shared seeds: why a seed path outside the project is refused, and what to do instead.

dbt writes each resource's compiled output at `target/<path relative to the
project>`. A seed path of `../../../shared/transform/seeds` therefore puts that
output three directories above target/ — next to the project's source files,
where no ignore rule reaches. The real-dbt test below pins that premise, so the
guard stays justified only for as long as dbt behaves this way.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest
from pf.runtime.dbt_runtime import declared_packages, escaping_paths, validate_paths
from pf.scaffold.bootstrap import _wire_group_package

DBT_PROJECT = """\
name: '{name}'
version: '1.0.0'
config-version: 2
profile: 'probe'
macro-paths: {macros}
seed-paths: {seeds}
"""

PROFILES = """\
probe:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: "{db}"
      threads: 1
"""


def _repo(tmp_path: Path, seeds: str = '["seeds"]', packages: str = "") -> Path:
    """A group with one shared seed, and one sister project."""
    (tmp_path / "platform").mkdir()
    shared = tmp_path / "groups" / "g" / "shared" / "transform"
    (shared / "seeds").mkdir(parents=True)
    (shared / "seeds" / "units.csv").write_text("unit_code,size\ng,0.001\nkg,1\n")
    (shared / "dbt_project.yml").write_text(
        DBT_PROJECT.format(name="g_shared", macros="[]", seeds='["seeds"]'))
    transform = tmp_path / "groups" / "g" / "projects" / "p" / "transform"
    transform.mkdir(parents=True)
    (transform / "dbt_project.yml").write_text(DBT_PROJECT.format(
        name="p", macros='["macros", "../../../../../platform/dbt/macros"]', seeds=seeds))
    (transform / "profiles.yml").write_text(PROFILES.format(db=transform / "p.duckdb"))
    if packages:
        (transform / "packages.yml").write_text(packages)
    return transform.parent


def test_a_seed_path_outside_the_project_is_flagged(tmp_path: Path) -> None:
    project = _repo(tmp_path, seeds='["seeds", "../../../shared/transform/seeds"]')
    assert escaping_paths(project) == [("seed-paths", "../../../shared/transform/seeds")]
    [issue] = validate_paths(project)
    assert issue.severity == "error" and "local package" in issue.message


@pytest.mark.parametrize("seeds", ['["seeds"]', '["data/../seeds"]', '["nested/seeds"]'])
def test_a_path_inside_the_project_is_not_flagged(tmp_path: Path, seeds: str) -> None:
    assert escaping_paths(_repo(tmp_path, seeds=seeds)) == []


def test_macro_paths_may_point_anywhere(tmp_path: Path) -> None:
    """Every project loads the platform macros from five levels up."""
    assert escaping_paths(_repo(tmp_path)) == []


def test_an_absolute_path_is_flagged(tmp_path: Path) -> None:
    project = _repo(tmp_path, seeds=f'["{tmp_path}"]')
    assert [k for k, _ in escaping_paths(project)] == ["seed-paths"]


PACKAGES = """\
# Packages for p. Comments here are load-bearing.
packages:
  - package: dbt-labs/dbt_utils
    version: [">=1.3.0", "<2.0.0"]
"""


def test_group_seeds_are_wired_as_a_local_package(tmp_path: Path) -> None:
    project = _repo(tmp_path, packages=PACKAGES)
    note = _wire_group_package(tmp_path, "g", project)
    text = (project / "transform" / "packages.yml").read_text()
    assert note and "  - local: ../../../shared/transform\n" in text
    assert text.startswith("# Packages for p. Comments here are load-bearing.")
    assert declared_packages(project) == 2


def test_wiring_is_idempotent(tmp_path: Path) -> None:
    project = _repo(tmp_path, packages=PACKAGES)
    _wire_group_package(tmp_path, "g", project)
    before = (project / "transform" / "packages.yml").read_text()
    assert _wire_group_package(tmp_path, "g", project) == ""
    assert (project / "transform" / "packages.yml").read_text() == before


def test_a_group_without_seeds_is_left_alone(tmp_path: Path) -> None:
    project = _repo(tmp_path, packages=PACKAGES)
    (tmp_path / "groups" / "g" / "shared" / "transform" / "seeds" / "units.csv").unlink()
    assert _wire_group_package(tmp_path, "g", project) == ""
    assert (project / "transform" / "packages.yml").read_text() == PACKAGES


def test_an_unparseable_layout_is_reported_not_rewritten(tmp_path: Path) -> None:
    project = _repo(tmp_path, packages="packages: []\n")
    note = _wire_group_package(tmp_path, "g", project)
    assert "add `- local: ../../../shared/transform`" in note
    assert (project / "transform" / "packages.yml").read_text() == "packages: []\n"


# The dbt installed next to this interpreter, not whichever `dbt` is first on
# PATH: a dbt Fusion preview there resolves a local package's seed path
# differently and fails, which says nothing about dbt Core's behaviour.
DBT = (str(Path(sys.executable).with_name("dbt"))
       if Path(sys.executable).with_name("dbt").exists() else shutil.which("dbt"))
NO_DBT = pytest.mark.skipif(DBT is None, reason="dbt not on PATH")


def _dbt(project: Path, *args: str) -> None:
    transform = project / "transform"
    proc = subprocess.run(
        [DBT, *args, "--project-dir", str(transform), "--profiles-dir", str(transform)],
        capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stdout[-2000:]


def _outside_target(tmp_path: Path, project: Path) -> set[str]:
    """Files dbt created that sit outside the project's generated directories."""
    generated = {"target", "dbt_packages", "logs"}
    out = set()
    for f in tmp_path.rglob("*"):
        if not f.is_file() or f.name in {"p.duckdb", "p.duckdb.wal", "package-lock.yml",
                                          ".user.yml"}:
            continue
        rel = f.relative_to(project / "transform") if project / "transform" in f.parents else None
        if rel is not None and rel.parts[0] in generated:
            continue
        out.add(str(f.relative_to(tmp_path)))
    return out


@NO_DBT
def test_dbt_really_writes_outside_target_for_an_escaping_seed_path(tmp_path: Path) -> None:
    project = _repo(tmp_path, seeds='["../../../shared/transform/seeds"]')
    sources = _outside_target(tmp_path, project)
    _dbt(project, "seed")
    assert _outside_target(tmp_path, project) - sources, \
        "dbt kept an escaping seed path inside target/ — the guard may be obsolete"


@NO_DBT
def test_a_group_package_keeps_every_artefact_inside_target(tmp_path: Path) -> None:
    project = _repo(tmp_path, seeds="[]", packages="packages:\n")
    assert _wire_group_package(tmp_path, "g", project)
    sources = _outside_target(tmp_path, project)
    _dbt(project, "deps")
    _dbt(project, "seed")
    assert _outside_target(tmp_path, project) == sources
    con = duckdb.connect(str(project / "transform" / "p.duckdb"), read_only=True)
    try:
        assert con.sql("select count(*) from units").fetchone()[0] == 2
    finally:
        con.close()


@NO_DBT
def test_a_package_wired_after_the_last_parse_is_installed(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The usual checkout has a manifest already. Wiring the group package into
    packages.yml must still get it installed, or the next dbt command fails on
    the missing package."""
    from pf.runtime.dbt_runtime import ensure_manifest

    monkeypatch.setenv("PATH", f"{Path(DBT).parent}{os.pathsep}{os.environ['PATH']}")
    project = _repo(tmp_path)  # no packages.yml yet; wiring creates it
    assert ensure_manifest(project)
    assert (project / "transform" / "target" / "manifest.json").exists()
    assert _wire_group_package(tmp_path, "g", project)
    assert ensure_manifest(project)
    assert (project / "transform" / "dbt_packages" / "g_shared" / "dbt_project.yml").exists()


def test_a_manifest_older_than_what_dbt_reads_is_stale(tmp_path: Path) -> None:
    """A manifest that merely exists is not current: an exposure written after it must force a parse.

    Trusting any existing manifest is how a laptop committed a graph missing
    every exposure its branch added, while the runner — which has no manifest
    and parses fresh — found them all and failed the PR.
    """
    from pf.runtime.dbt_runtime import manifest_is_stale

    transform = tmp_path / "transform"
    (transform / "models").mkdir(parents=True)
    model = transform / "models" / "m.sql"
    model.write_text("select 1")
    assert manifest_is_stale(tmp_path), "no manifest at all"

    manifest = transform / "target" / "manifest.json"
    manifest.parent.mkdir()
    manifest.write_text("{}")
    os.utime(model, (1, 1))
    assert not manifest_is_stale(tmp_path)

    later = manifest.stat().st_mtime + 10
    # What dbt writes or installs is never an edit.
    for out in ("target/run_results.json", "dbt_packages/p/models/x.sql", "logs/dbt.log", ".user.yml"):
        (transform / out).parent.mkdir(parents=True, exist_ok=True)
        (transform / out).write_text("x")
        os.utime(transform / out, (later, later))
    assert not manifest_is_stale(tmp_path)

    exposures = transform / "models" / "_exposures.yml"
    exposures.write_text("exposures: []")
    os.utime(exposures, (later, later))
    assert manifest_is_stale(tmp_path)
