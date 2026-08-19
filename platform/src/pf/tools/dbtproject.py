"""Idempotent edits to a project's dbt files, for tools that ship dbt packages.

A tool like Elementary or dbt-expectations is not a binary bolted onto the
side of dbt — it *is* a dbt package, and "enabled" means "declared in this
project's `packages.yml` and configured in its `dbt_project.yml`". Those two
files are project-owned: the scaffolder writes them once and people edit them
afterwards, so a tool cannot regenerate them from a template the way recce
regenerates `recce.yml`. What it can do is make the smallest edit that
establishes its declaration, and make it again harmlessly on every
`pf bootstrap` — which is what everything here does.

Two editing disciplines, chosen per file by what the file holds:

  * **`packages.yml` round-trips through YAML.** Every project's copy is
    machine-shaped (the scaffolder's template has no comments and nobody adds
    any — it is a lockfile-adjacent list), so parse → merge → dump is safe, and
    it is the only way to answer "is this package already declared" without
    guessing at formatting. An existing declaration of the same package is
    **never touched**: a human's pin is a decision, and a tool that fights it
    turns every bootstrap into an argument.

  * **`dbt_project.yml` and `profiles.yml` get appended to, never rewritten.**
    Both carry hand-written comments that explain real decisions (why the
    platform macros load unqualified, why `base` must be a separate
    materialisation), and a YAML round-trip would silently delete them. An
    append of a new top-level key, or an insert directly under an existing
    one, preserves every byte that was already there. Presence is still
    checked by parsing, so idempotence does not depend on string matching.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    """One YAML mapping, or empty. A missing or broken file reads as empty —
    the callers below only ever use this to ask "is X already declared", and
    for a file that cannot be parsed the honest answer is no."""
    if not path.exists():
        return {}
    try:
        doc = yaml.safe_load(path.read_text())
    except yaml.YAMLError:
        return {}
    return doc if isinstance(doc, dict) else {}


# ------------------------------------------------------------ packages.yml --
def has_package(dbt_dir: Path, package: str) -> bool:
    """Is `org/name` declared, under either dbt dependency file?"""
    for fname in ("packages.yml", "dependencies.yml"):
        doc = load_yaml(dbt_dir / fname)
        for entry in doc.get("packages") or []:
            if isinstance(entry, dict) and entry.get("package") == package:
                return True
    return False


def ensure_package(dbt_dir: Path, package: str, version: list[str]) -> bool:
    """Declare a hub package in `packages.yml`. Returns True if it was added.

    Already declared — at any version — means untouched: the project's pin is
    the project's decision. `dependencies.yml` counts as declared too, but new
    entries always go to `packages.yml`; a project using `dependencies.yml`
    for hub packages has made a layout choice this helper should follow, and
    the first bootstrap on such a project will surface that as a one-time
    manual move rather than silently forking the declaration across two files.

    The write is a YAML round-trip, so a comment someone adds to this file
    would be lost on the *next* package addition. See the module docstring for
    why that trade is taken here and refused for `dbt_project.yml`.
    """
    if has_package(dbt_dir, package):
        return False
    path = dbt_dir / "packages.yml"
    doc = load_yaml(path)
    packages = doc.setdefault("packages", [])
    packages.append({"package": package, "version": list(version)})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    return True


# --------------------------------------------------------- dbt_project.yml --
def has_project_key(dbt_dir: Path, *keys: str) -> bool:
    """Does dbt_project.yml already hold this key path?"""
    node: Any = load_yaml(dbt_dir / "dbt_project.yml")
    for k in keys:
        if not isinstance(node, dict) or k not in node:
            return False
        node = node[k]
    return True


def insert_under_key(path: Path, top_key: str, block: str) -> bool:
    """Insert `block` as the first child of a top-level mapping key, or append
    `top_key:\\n<block>` at the end when the key does not exist yet.

    Text surgery, not a YAML dump: the point is to leave every existing line —
    comments included — exactly as it was. `block` must already be indented as
    a child of `top_key` (two spaces). Mapping order is irrelevant to dbt, so
    "first child" is chosen only because the top of the block is the one place
    that provably exists.

    The caller is responsible for the presence check (`has_project_key`);
    this function only edits.
    """
    text = path.read_text() if path.exists() else ""
    if not block.endswith("\n"):
        block += "\n"
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        # A top-level key is unindented. Matching the line, not the parsed
        # document, is safe here because the caller already parsed the file to
        # decide the insert is needed at all.
        if line.split("#", 1)[0].rstrip() == f"{top_key}:":
            lines.insert(i + 1, block)
            path.write_text("".join(lines))
            return True
    tail = "" if text.endswith("\n") or not text else "\n"
    path.write_text(text + tail + f"{top_key}:\n" + block)
    return True


# ------------------------------------------------------------ profiles.yml --
def has_profile(dbt_dir: Path, name: str) -> bool:
    return name in load_yaml(dbt_dir / "profiles.yml")


def append_profile(dbt_dir: Path, name: str, block: str) -> bool:
    """Append one top-level profile to profiles.yml. Returns True if added.

    An append rather than a merge because a new top-level key at the end of a
    YAML document is always valid and touches nothing above it. The platform
    regenerates profiles.yml wholesale in a few places (`write_profiles`), so
    a profile added this way can disappear on a retrofit — which is exactly
    why the tools that need one re-add it on every `pf bootstrap`, and why a
    tool doing so should order itself `after` the tools that rewrite.
    """
    if has_profile(dbt_dir, name):
        return False
    path = dbt_dir / "profiles.yml"
    text = path.read_text() if path.exists() else ""
    if text and not text.endswith("\n"):
        text += "\n"
    if not block.endswith("\n"):
        block += "\n"
    path.write_text(text + block)
    return True


def replace_profile(dbt_dir: Path, name: str, block: str) -> bool:
    """Write one top-level profile, replacing any previous version of it.
    Returns True if the file changed.

    `append_profile` is for a block whose content never moves. This is for a
    *derived* profile — one computed from the rest of the file — which goes
    stale the moment the project's own targets change (a warehouse capability
    swapping `prod`, say) and must be re-emitted rather than left as written.

    The replacement span is the profile's top-level key through the last line
    of its indented body, plus the contiguous comment block sitting directly
    above it — comments travel with the block that explains them, and leaving
    the old ones behind would stack a new header on a stale explanation.
    Everything else in the file is untouched, byte for byte.
    """
    path = dbt_dir / "profiles.yml"
    text = path.read_text() if path.exists() else ""
    if not block.endswith("\n"):
        block += "\n"

    lines = text.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines)
                  if line.split("#", 1)[0].rstrip() == f"{name}:"), None)
    if start is None:
        if text and not text.endswith("\n"):
            text += "\n"
        # The same one-blank-line separator the replacement path emits, so the
        # first write and every rewrite produce byte-identical files — without
        # it, the second bootstrap "changes" the file by adding the separator.
        path.write_text(text + ("\n" if text else "") + block)
        return True

    s = start
    while s > 0 and lines[s - 1].lstrip().startswith("#"):
        s -= 1
    while s > 0 and lines[s - 1].strip() == "":
        s -= 1
    e = start + 1
    while e < len(lines):
        line = lines[e]
        # The body is everything indented or blank. A column-zero line — key
        # or comment — belongs to whatever comes next.
        if line.strip() == "" or line[0] in (" ", "\t"):
            e += 1
            continue
        break

    new = "".join(lines[:s]) + ("\n" if s > 0 else "") + block + "".join(lines[e:])
    if new == text:
        return False
    path.write_text(new)
    return True
