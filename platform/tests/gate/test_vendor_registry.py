"""The vendor registry parses and names files that exist.

`platform/src/pf/vendor/registry.yaml` is read by `pf vendor why`, the
`vendor docs` bootstrap step and the vendor-drift loop, all through one
`yaml.safe_load` with nothing to catch a mistake. A port entry indented one
level too deep took every reader down at once and nothing in the suite noticed,
because no test had ever loaded the file.
"""

from __future__ import annotations

from pathlib import Path

from conftest import REPO_ROOT
from pf.vendor.model import REGISTRY, load_registry

ROOT = REPO_ROOT


def test_the_registry_parses_into_upstreams_with_ports() -> None:
    upstreams = load_registry(REGISTRY)
    assert len(upstreams) >= 14
    assert all(u.id and u.path for u in upstreams)


def test_every_adopted_entry_names_a_file_of_ours_that_exists() -> None:
    """An `ours:` path that does not exist is a provenance record for nothing,
    and `pf vendor why <file>` can never find it."""
    missing = sorted(
        o for u in load_registry(REGISTRY) for a in u.adopted for o in a.ours
        if not (ROOT / o).exists())
    assert missing == []
