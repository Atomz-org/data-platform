"""Migrations for a project's `.claude/settings.json`.

Claude Code validates settings against a schema, and a key with the wrong
*shape* is not a warning — the file fails validation and the plugins it declares
never load. That failure is silent from inside a session: `power-tools@platform`
is simply absent, so `kg_search`, `kg_neighbors`, `kg_path` and `impact_analysis`
do not exist, and an agent told by CLAUDE.md to ask the graph first reads files
instead and never says why.

Two shapes shipped wrong and reached every project the scaffolder wrote:

    enabledPlugins        was a list of `plugin@marketplace` ids
                          is a record keyed by that id, with a boolean value

    marketplace source    was `{"source": "<path>"}`
                          is `{"source": "directory", "path": "<path>"}` —
                          the inner `source` names the *kind* of source, and a
                          bare path is not one of the kinds

Both live here rather than in the generator because a template only fixes the
projects written after it. The projects that already exist need the same
knowledge applied to a file on disk, which is what `normalize` is for and what
the `claude settings` bootstrap step calls it for.

Every migration is a no-op on already-current settings, so this is safe to run
on every bootstrap — the step reports what it changed, and changes nothing twice.
"""

from __future__ import annotations

from typing import Any

#: The `source.source` discriminator values Claude Code accepts. A marketplace
#: whose `source.source` is none of these is a pre-migration entry holding a bare
#: path — see `_migrate_marketplaces`. Kept as a set rather than checked with
#: "does it look like a path" because the failure mode of guessing wrong is a
#: marketplace that silently stops resolving, and an unknown *new* source kind
#: should be left alone rather than rewritten into a directory source.
SOURCE_KINDS = frozenset({
    "github", "git", "npm", "url", "file", "directory", "settings",
})


def _migrate_plugins(settings: dict[str, Any]) -> str | None:
    """`enabledPlugins` list -> record. Returns a description, or None."""
    plugins = settings.get("enabledPlugins")
    if not isinstance(plugins, list):
        return None
    # Order is not meaningful in the record form, and every id in the legacy
    # list was by definition enabled — an id could not appear in it and be off.
    settings["enabledPlugins"] = dict.fromkeys(plugins, True)
    return f"enabledPlugins: list -> record ({len(plugins)} plugin(s))"


def _migrate_marketplaces(settings: dict[str, Any]) -> list[str]:
    """Bare-path marketplace sources -> explicit directory sources."""
    marketplaces = settings.get("extraKnownMarketplaces")
    if not isinstance(marketplaces, dict):
        return []

    changed: list[str] = []
    for name, entry in marketplaces.items():
        if not isinstance(entry, dict):
            continue
        source = entry.get("source")
        if not isinstance(source, dict):
            continue
        kind = source.get("source")
        # Already current, or a source kind this version of the platform does
        # not know about. Either way it is not ours to rewrite.
        if not isinstance(kind, str) or kind in SOURCE_KINDS:
            continue
        # The only shape that ever shipped wrong put the path where the kind
        # belongs. Anything else — a dict, a number — is not a path we can
        # rescue, and guessing would replace a broken entry with a wrong one.
        entry["source"] = {"source": "directory", "path": kind}
        changed.append(f"marketplace {name!r}: bare path -> directory source")
    return changed


def normalize(settings: dict[str, Any]) -> list[str]:
    """Migrate `settings` in place. Returns one line per change, empty if current.

    The caller decides whether to write: an empty return means the file on disk
    is already correct and rewriting it would be churn in a diff for no reason.
    """
    changes: list[str] = []
    if (plugins := _migrate_plugins(settings)) is not None:
        changes.append(plugins)
    changes.extend(_migrate_marketplaces(settings))
    return changes


def ensure_plugins(settings: dict[str, Any], wanted: dict[str, bool]) -> list[str]:
    """Enable toolkits this project is missing. Returns one line per change.

    The mirror of `Capability.default_enabled` for plugins: a toolkit added to
    `DEFAULT_TOOLKITS` today must reach the projects scaffolded before it existed,
    or it is a toolkit only new projects have and nobody can see that from inside
    an old one.

    **Only ever adds.** A plugin the project has set to `false` stays `false` —
    that is somebody's deliberate opt-out, and a bootstrap that silently undoes it
    is a bootstrap people stop running. Nothing is removed either: a project may
    enable toolkits beyond the platform default, and this has no opinion on those.
    """
    current = settings.setdefault("enabledPlugins", {})
    if not isinstance(current, dict):
        # `normalize` runs first in the one caller that matters; a caller that
        # skipped it gets told which step it skipped rather than a TypeError.
        raise TypeError("enabledPlugins is not a record — run normalize() first")

    added = [name for name in wanted if name not in current]
    for name in added:
        current[name] = wanted[name]
    return [f"enabled {name}" for name in added]
