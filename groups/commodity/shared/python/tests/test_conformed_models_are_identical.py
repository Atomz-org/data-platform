"""The conformed layer is the same file in every sister.

`intermediate/`, `marts/core/`, `semantic/` and `utils/` are what the roll-up
unions and what a metric name means across markets. A sister that edits her
copy has forked the family's vocabulary; this test names the file. A sister
may *add* models (`marts/<market>/`) freely — only the conformed paths are
compared.

A market's own source is not conformed either. Staging for the group's
connectors (`commodity_shared.<module>`) is identical everywhere because every
sister lands the same feed; a feed only one market has — India's MCX bhavcopy —
stages in `staging/<source>/` and builds in `intermediate/<source>/`, and the
other sisters have nothing to be identical to. Such a source is named in the
sister's `contracts/annotations.yaml` and is not a group connector; both
directories of it are left out of the comparison, and nothing else is.
"""

import hashlib
from pathlib import Path

import pytest
import yaml

GROUP = Path(__file__).resolve().parents[3]
CONFORMED = ("models/intermediate", "models/marts/core", "models/semantic", "models/utils",
             "models/staging")


def sisters() -> list[Path]:
    return sorted(p for p in (GROUP / "projects").iterdir()
                  if p.is_dir() and not p.name.endswith("-rollup")
                  and (p / "transform" / "models" / "marts" / "core").is_dir())


def group_connectors() -> set[str]:
    return {f.stem for f in (GROUP / "shared" / "python" / "src" / "commodity_shared").glob("*.py")
            if not f.stem.startswith("_")}


def local_sources(project: Path) -> set[str]:
    """Sources this sister lands that no group connector provides."""
    ann = project / "contracts" / "annotations.yaml"
    if not ann.exists():
        return set()
    resources = (yaml.safe_load(ann.read_text(encoding="utf-8")) or {}).get("resources") or []
    return {r["source"] for r in resources if r.get("source")} - group_connectors()


def is_local(rel: Path, local: set[str]) -> bool:
    """`models/staging/mcx/...` or `models/intermediate/mcx/...` for a local source."""
    parts = rel.parts
    return len(parts) > 3 and parts[1] in ("staging", "intermediate") and parts[2] in local


def digest(project: Path) -> dict[str, str]:
    out = {}
    local = local_sources(project)
    for rel in CONFORMED:
        base = project / "transform" / rel
        for f in sorted(base.rglob("*")):
            path = f.relative_to(project / "transform")
            if f.is_file() and f.suffix in {".sql", ".yml"} and not is_local(path, local):
                out[str(path)] = hashlib.sha256(f.read_bytes()).hexdigest()
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


def test_only_a_market_local_source_is_exempt():
    """The exemption is a directory named for a local source, in staging or
    intermediate — never a conformed model that happens to share a word."""
    local = {"mcx"}
    assert is_local(Path("models/staging/mcx/stg_mcx__futures_bhavcopy.sql"), local)
    assert is_local(Path("models/intermediate/mcx/int_mcx__futures_sessions.sql"), local)
    assert not is_local(Path("models/staging/yahoo_finance/stg_yahoo_finance__fx_rates.sql"), local)
    assert not is_local(Path("models/intermediate/int_fx_rates__daily.sql"), local)
    assert not is_local(Path("models/marts/core/mcx/x.sql"), local)
    assert not ({"yahoo_finance", "gold_api"} & (local_sources(GROUP / "projects" / "commodity-india")))
