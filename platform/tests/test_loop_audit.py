"""Tests for the Loop Readiness Score.

The check worth pinning is the one that failed silently for every group: a
group marketplace that lists `./.claude` as a plugin while nothing makes that
directory a plugin. `claude plugin validate` reports it, but the audit is what
runs where that CLI is not installed, so the audit has to report it too.
"""

from __future__ import annotations

import json
from pathlib import Path

from pf.loops.audit import Check, audit


def _group(root: Path, name: str, *, marketplace: bool = True,
           manifest: bool = True) -> None:
    """The minimum a group needs on disk for the audit to have an opinion."""
    gdir = root / "groups" / name
    (gdir / ".claude" / "skills").mkdir(parents=True)
    if marketplace:
        (gdir / ".claude-plugin").mkdir()
        (gdir / ".claude-plugin" / "marketplace.json").write_text(json.dumps({
            "name": name,
            "plugins": [{"name": f"{name}-group", "source": "./.claude"}],
        }))
    if manifest:
        (gdir / ".claude" / ".claude-plugin").mkdir()
        (gdir / ".claude" / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": f"{name}-group", "version": "0.1.0"}))


def _check(root: Path, name: str) -> Check:
    _, checks = audit(root)
    return next(c for c in checks if c.name == name)


def test_passes_when_every_group_plugin_has_a_manifest(tmp_path: Path) -> None:
    _group(tmp_path, "alpha")
    _group(tmp_path, "beta")
    check = _check(tmp_path, "group plugins resolve")
    assert check.passed
    assert check.detail == "2 group plugin(s) resolve"


def test_fails_naming_the_group_without_a_manifest(tmp_path: Path) -> None:
    _group(tmp_path, "alpha")
    _group(tmp_path, "beta", manifest=False)
    check = _check(tmp_path, "group plugins resolve")
    assert not check.passed
    assert "beta" in check.detail
    assert "alpha" not in check.detail


def test_group_without_a_marketplace_is_ignored(tmp_path: Path) -> None:
    _group(tmp_path, "alpha")
    _group(tmp_path, "beta", marketplace=False, manifest=False)
    check = _check(tmp_path, "group plugins resolve")
    assert check.passed
    assert check.detail == "1 group plugin(s) resolve"


def test_group_check_is_weighted_into_the_total(tmp_path: Path) -> None:
    # The score divides by the sum of the list, so a new check must appear in
    # it with its weight rather than be added to a hand-kept constant.
    _, checks = audit(tmp_path)
    check = next(c for c in checks if c.name == "group plugins resolve")
    assert check.weight == 5
    assert sum(c.weight for c in checks) >= 5 + 100
