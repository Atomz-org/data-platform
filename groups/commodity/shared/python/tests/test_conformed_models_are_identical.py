"""The conformed layer is the same file in every sister.

`intermediate/`, `marts/core/`, `semantic/` and `utils/` are what the roll-up
unions and what a metric name means across markets. A sister that edits her
copy has forked the family's vocabulary; this test names the file. A sister
may *add* models (`marts/<market>/`) freely — only the conformed paths are
compared.
"""

import hashlib
from pathlib import Path

import pytest

GROUP = Path(__file__).resolve().parents[3]
CONFORMED = ("models/intermediate", "models/marts/core", "models/semantic", "models/utils",
             "models/staging")


def sisters() -> list[Path]:
    return sorted(p for p in (GROUP / "projects").iterdir()
                  if p.is_dir() and not p.name.endswith("-rollup")
                  and (p / "transform" / "models" / "marts" / "core").is_dir())


def digest(project: Path) -> dict[str, str]:
    out = {}
    for rel in CONFORMED:
        base = project / "transform" / rel
        for f in sorted(base.rglob("*")):
            if f.is_file() and f.suffix in {".sql", ".yml"}:
                out[str(f.relative_to(project / "transform"))] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


@pytest.mark.parametrize("sister", sisters(), ids=lambda p: p.name)
def test_conformed_files_match_the_first_sister(sister):
    reference, *_ = sisters()
    if sister == reference:
        pytest.skip("the reference copy")
    ours, theirs = digest(sister), digest(reference)
    drift = sorted(f for f in set(ours) | set(theirs) if ours.get(f) != theirs.get(f))
    assert not drift, f"{sister.name} differs from {reference.name} in: " + ", ".join(drift)


def test_the_family_has_sisters_to_compare():
    """One sister conforms with nobody; the comparison above is vacuous until a
    second exists. Skipped rather than failed so a family of one still tests."""
    if len(sisters()) < 2:
        pytest.skip(f"only {[p.name for p in sisters()]} — nothing to compare yet")
    assert len(sisters()) >= 2
