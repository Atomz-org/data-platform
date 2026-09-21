"""Memory index and the layout that makes a note findable.

A lesson written into a directory nobody indexes is the silent failure this
guards: the note exists, the author believes it is known, and the next session
— Claude's or Copilot's — never sees it. So the index is checked by the notes
it describes, every note must sit in a module the index looks at, and the index
stays small enough to be read rather than skipped.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import REPO_ROOT
from pf.memory import (
    INDEX_BUDGET,
    README_TEXT,
    add,
    drift,
    index_path,
    init_readmes,
    module_for,
    module_roots,
    notes_dir,
    relevant,
    render_index,
    scan,
    visible_from,
)


def test_the_committed_index_matches_the_notes() -> None:
    """Run `uv run pf memory index` if this fails — the notes are the source."""
    assert drift(REPO_ROOT) == ""


def test_every_note_has_a_line_to_index() -> None:
    silent = [str(n.path.relative_to(REPO_ROOT)) for n in scan(REPO_ROOT) if not n.description]
    assert not silent, f"{silent} have no description — the index would show a blank row"


def test_every_note_sits_in_a_module_the_index_reads() -> None:
    """`.memory/notes/*.md` anywhere else is invisible to every agent."""
    known = {notes_dir(REPO_ROOT, m).resolve() for m, _ in module_roots(REPO_ROOT)}
    skip = {"vendor", ".venv", "node_modules", ".git", "okf"}
    stray = []
    for d in REPO_ROOT.rglob("notes"):
        if d.parent.name != ".memory" or not d.is_dir():
            continue
        if any(part in skip for part in d.relative_to(REPO_ROOT).parts):
            continue
        if d.resolve() not in known and any(p.name.lower() != "readme.md" for p in d.glob("*.md")):
            stray.append(str(d.relative_to(REPO_ROOT)))
    assert not stray, f"memory notes outside every module: {stray}"


def test_the_index_is_deterministic() -> None:
    """Compared byte for byte, so rendering twice must agree."""
    notes = scan(REPO_ROOT)
    assert render_index(notes, REPO_ROOT) == render_index(scan(REPO_ROOT), REPO_ROOT)
    assert render_index(notes, REPO_ROOT) == render_index(list(reversed(notes)), REPO_ROOT)


def test_every_link_in_the_index_resolves() -> None:
    """The index lives in `.memory/`, so its links are relative to that dir."""
    import re

    idx = index_path(REPO_ROOT)
    if not idx.exists():
        pytest.skip("no index yet")
    targets = re.findall(r"\]\(([^)]+\.md)\)", idx.read_text(encoding="utf-8"))
    broken = [t for t in targets if not (idx.parent / t).exists()]
    assert not broken, f"index links point at nothing: {broken}"


def test_the_index_is_small_enough_to_be_worth_reading() -> None:
    """When this binds, roll a module up rather than raising the number."""
    idx = index_path(REPO_ROOT)
    if not idx.exists():
        pytest.skip("no index yet")
    approx = len(idx.read_text(encoding="utf-8")) // 4
    assert approx < INDEX_BUDGET, (
        f"the memory index is ~{approx} tokens; summarise a module rather than listing every note"
    )


def test_visibility_never_crosses_a_sister() -> None:
    """A project reads root, platform, its group and itself — the same set its
    `.claude/settings.json` Read denylist permits, and nothing more."""
    assert visible_from("root") == ["root", "platform"]
    assert visible_from("platform") == ["root", "platform"]
    assert visible_from("groups/acme") == ["root", "platform", "groups/acme"]
    assert visible_from("groups/acme/projects/acme-us") == [
        "root",
        "platform",
        "groups/acme",
        "groups/acme/projects/acme-us",
    ]
    assert "groups/acme/projects/acme-eu" not in visible_from("groups/acme/projects/acme-us")


def test_module_is_resolved_from_where_you_are() -> None:
    assert module_for(REPO_ROOT, REPO_ROOT) == "root"
    assert module_for(REPO_ROOT, REPO_ROOT / "platform" / "src") == "platform"
    assert module_for(REPO_ROOT, REPO_ROOT / "groups" / "acme") == "groups/acme"
    assert module_for(REPO_ROOT, REPO_ROOT / "groups" / "acme" / "projects" / "acme-us" / "transform") == (
        "groups/acme/projects/acme-us"
    )


def _skeleton(tmp_path: Path) -> Path:
    """The two marker directories and one group with one project."""
    (tmp_path / "platform").mkdir()
    (tmp_path / "groups" / "g" / "projects" / "p").mkdir(parents=True)
    return tmp_path


def test_add_writes_the_note_and_the_index_together(tmp_path: Path) -> None:
    root = _skeleton(tmp_path)
    p = add(root, "groups/g/projects/p", "first-lesson", "one line", body="why\n\nhow", type_="project")
    assert p == root / "groups" / "g" / "projects" / "p" / ".memory" / "notes" / "first-lesson.md"
    assert drift(root) == "", "add must leave the index current"
    text = index_path(root).read_text(encoding="utf-8")
    assert "first-lesson" in text and "one line" in text
    assert [n.name for n in relevant(root, "groups/g/projects/p")] == ["first-lesson"]
    assert relevant(root, "root") == [], "a project's note is not visible from the root"


def test_add_refuses_what_would_make_the_index_lie(tmp_path: Path) -> None:
    root = _skeleton(tmp_path)
    with pytest.raises(ValueError):
        add(root, "root", "Not A Slug", "x")
    with pytest.raises(ValueError):
        add(root, "root", "fine", "")
    with pytest.raises(ValueError):
        add(root, "root", "fine", "x", type_="opinion")
    with pytest.raises(KeyError):
        add(root, "groups/nope", "fine", "x")
    add(root, "root", "fine", "x")
    with pytest.raises(FileExistsError):
        add(root, "root", "fine", "again")


def test_a_note_copied_from_claudes_store_is_valid_here(tmp_path: Path) -> None:
    """Claude's own store nests `type` under `metadata:`; both shapes parse."""
    root = _skeleton(tmp_path)
    d = notes_dir(root, "platform")
    d.mkdir(parents=True)
    (d / "nested.md").write_text(
        "---\nname: nested\ndescription: from the home store\nmetadata:\n  type: feedback\n---\nbody\n",
        encoding="utf-8",
    )
    (d / "flat.md").write_text("---\nname: flat\ndescription: flat\ntype: reference\n---\n", encoding="utf-8")
    kinds = {n.name: n.type for n in scan(root)}
    assert kinds == {"nested": "feedback", "flat": "reference"}


def test_init_readmes_is_idempotent_and_never_overwrites(tmp_path: Path) -> None:
    root = _skeleton(tmp_path)
    first = init_readmes(root)
    assert {p.parent.parent.parent.name for p in first} >= {"platform", "g", "p"}
    custom = notes_dir(root, "platform") / "README.md"
    custom.write_text("mine", encoding="utf-8")
    assert init_readmes(root) == []
    assert custom.read_text(encoding="utf-8") == "mine"
    assert (notes_dir(root, "root") / "README.md").read_text(encoding="utf-8") == README_TEXT


def test_every_module_in_this_repo_has_its_readme() -> None:
    """The directory exists in git only because the README does."""
    missing = [m for m, _ in module_roots(REPO_ROOT) if not (notes_dir(REPO_ROOT, m) / "README.md").exists()]
    assert not missing, f"run `uv run pf memory init`: {missing}"
