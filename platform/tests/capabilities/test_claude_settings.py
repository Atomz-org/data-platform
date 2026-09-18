"""Tests for the `.claude/settings.json` schema migrations.

The properties worth pinning down are the ones that made the original bug
expensive: that the migration is idempotent (it runs on every bootstrap), that
it does not touch settings it does not understand, that the scaffolder no longer
emits the broken shapes, and that a capability can still merge into a project
that has not been migrated yet — the combination that previously turned
`pf bootstrap` into an AttributeError.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pf.capabilities import Capability, _merge
from pf.capabilities import apply as apply_capability
from pf.scaffold.claude_settings import SOURCE_KINDS, ensure_plugins, normalize
from pf.scaffold.generator import DEFAULT_TOOLKITS, PROJECT_SETTINGS, default_plugins


# ------------------------------------------------------------ enabledPlugins --
def test_plugin_list_becomes_a_record() -> None:
    settings = {"enabledPlugins": ["a@platform", "b@platform"]}
    changes = normalize(settings)
    assert settings["enabledPlugins"] == {"a@platform": True, "b@platform": True}
    assert len(changes) == 1


def test_plugin_record_is_left_alone() -> None:
    """Including the explicit `false` a user set to turn one plugin off."""
    settings = {"enabledPlugins": {"a@platform": True, "b@platform": False}}
    assert normalize(settings) == []
    assert settings["enabledPlugins"] == {"a@platform": True, "b@platform": False}


# -------------------------------------------------------------- marketplaces --
def test_bare_path_source_becomes_a_directory_source() -> None:
    settings = {"extraKnownMarketplaces": {
        "platform": {"source": {"source": "../../../../platform"}}}}
    normalize(settings)
    assert settings["extraKnownMarketplaces"]["platform"]["source"] == {
        "source": "directory", "path": "../../../../platform"}


@pytest.mark.parametrize("kind", sorted(SOURCE_KINDS))
def test_known_source_kinds_are_never_rewritten(kind: str) -> None:
    """A github source must survive a migration aimed at bare paths."""
    settings = {"extraKnownMarketplaces": {
        "m": {"source": {"source": kind, "repo": "owner/repo"}}}}
    assert normalize(settings) == []
    assert settings["extraKnownMarketplaces"]["m"]["source"]["source"] == kind


def test_unrecognised_shapes_are_left_for_a_human() -> None:
    """Not every wrong value is a rescuable path; guessing would make it worse."""
    settings = {"extraKnownMarketplaces": {"m": {"source": {"source": {"nested": 1}}}}}
    assert normalize(settings) == []


# ---------------------------------------------------------------- idempotence --
def test_normalize_is_idempotent() -> None:
    """`pf bootstrap --all` is expected to be run repeatedly."""
    settings = {
        "enabledPlugins": ["a@platform"],
        "extraKnownMarketplaces": {"platform": {"source": {"source": "../x"}}},
    }
    assert len(normalize(settings)) == 2
    first = json.dumps(settings, sort_keys=True)
    assert normalize(settings) == []          # second pass reports nothing
    assert json.dumps(settings, sort_keys=True) == first


def test_unrelated_settings_survive() -> None:
    settings = {"permissions": {"allow": ["Bash(pf:*)"]}, "env": {"PF_NOTIFY": "1"},
                "enabledPlugins": ["a@platform"]}
    normalize(settings)
    assert settings["permissions"] == {"allow": ["Bash(pf:*)"]}
    assert settings["env"] == {"PF_NOTIFY": "1"}


# ------------------------------------------------------------ the scaffolder --
def test_generated_settings_are_schema_valid() -> None:
    """The template must not re-emit what the migration exists to repair."""
    rendered = (PROJECT_SETTINGS
                .replace("{{group}}", "acme")
                .replace("{{deny_siblings}}", '"Read(../other/**)"'))
    settings = json.loads(rendered)

    assert isinstance(settings["enabledPlugins"], dict)
    assert all(v is True for v in settings["enabledPlugins"].values())
    for name, entry in settings["extraKnownMarketplaces"].items():
        assert entry["source"]["source"] in SOURCE_KINDS, name
        assert entry["source"]["path"], name
    # A fresh render needs no migration — otherwise the template and the
    # migration disagree about what "current" means.
    assert normalize(settings) == []


# ------------------------------------------------------------------- merging --
def test_capability_record_merges_into_a_legacy_project(tmp_path: Path) -> None:
    """The crash this whole change exists to prevent.

    A capability contributing `enabledPlugins` as a record, applied to a project
    whose settings still hold the list, used to raise AttributeError inside
    `_merge` — one schema version behind became a hard bootstrap failure.
    """
    claude = tmp_path / ".claude"
    claude.mkdir()
    (claude / "settings.json").write_text(json.dumps(
        {"enabledPlugins": ["old@platform"]}))

    cap = Capability(name="c", description="d",
                     settings={"enabledPlugins": {"new@platform": True}})
    apply_capability(cap, tmp_path, tmp_path, {})

    assert json.loads((claude / "settings.json").read_text())["enabledPlugins"] == {
        "old@platform": True, "new@platform": True}


def test_merge_names_the_key_it_cannot_reconcile() -> None:
    """An unmigratable conflict must say which setting, not AttributeError."""
    base = {"permissions": "not-an-object"}
    with pytest.raises(TypeError, match="permissions"):
        _merge(base, {"permissions": {"allow": ["x"]}})


def test_merge_still_appends_lists() -> None:
    """The existing contract: capabilities add permissions, never replace them."""
    base = {"permissions": {"allow": ["Bash(a:*)"]}}
    _merge(base, {"permissions": {"allow": ["Bash(a:*)", "Bash(b:*)"]}})
    assert base["permissions"]["allow"] == ["Bash(a:*)", "Bash(b:*)"]


# --------------------------------------------------------- toolkit backfill --
def test_missing_toolkits_are_enabled() -> None:
    settings = {"enabledPlugins": {"platform-init@platform": True}}
    changes = ensure_plugins(settings, {"platform-init@platform": True,
                                        "dbt-elementary@platform": True})
    assert settings["enabledPlugins"]["dbt-elementary@platform"] is True
    assert changes == ["enabled dbt-elementary@platform"]


def test_an_explicit_opt_out_is_never_undone() -> None:
    """A bootstrap that silently re-enables what you turned off stops being run."""
    settings = {"enabledPlugins": {"dbt-elementary@platform": False}}
    assert ensure_plugins(settings, {"dbt-elementary@platform": True}) == []
    assert settings["enabledPlugins"]["dbt-elementary@platform"] is False


def test_extra_plugins_are_left_alone() -> None:
    """A project may enable toolkits beyond the default; this has no opinion."""
    settings = {"enabledPlugins": {"something-local@elsewhere": True}}
    ensure_plugins(settings, {"platform-init@platform": True})
    assert settings["enabledPlugins"]["something-local@elsewhere"] is True


def test_ensure_plugins_is_idempotent() -> None:
    settings = {"enabledPlugins": {}}
    wanted = {"a@platform": True, "b@platform": True}
    assert len(ensure_plugins(settings, wanted)) == 2
    assert ensure_plugins(settings, wanted) == []


def test_ensure_plugins_names_the_step_you_skipped() -> None:
    with pytest.raises(TypeError, match="normalize"):
        ensure_plugins({"enabledPlugins": ["a@platform"]}, {"b@platform": True})


# ------------------------------------------------------- one source of truth --
def test_the_template_matches_default_plugins() -> None:
    """Two copies of this list is how a toolkit reaches only new projects."""
    rendered = json.loads(PROJECT_SETTINGS
                          .replace("{{group}}", "acme")
                          .replace("{{deny_siblings}}", '"Read(../other/**)"'))
    assert rendered["enabledPlugins"] == default_plugins("acme")


def test_every_default_toolkit_exists_on_disk() -> None:
    """A toolkit enabled everywhere that has no directory is a broken plugin id."""
    from conftest import REPO_ROOT
    for name in DEFAULT_TOOLKITS:
        assert (REPO_ROOT / "platform" / "toolkits" / name).is_dir(), name


def test_every_default_toolkit_is_in_the_marketplace() -> None:
    from conftest import REPO_ROOT
    manifest = json.loads(
        (REPO_ROOT / "platform" / ".claude-plugin" / "marketplace.json").read_text())
    listed = {p["name"] for p in manifest["plugins"]}
    assert set(DEFAULT_TOOLKITS) <= listed, sorted(set(DEFAULT_TOOLKITS) - listed)
