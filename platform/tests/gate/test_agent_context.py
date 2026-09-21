"""The entry points every tool reads agree with each other and with the protocol.

`GEMINI.md` importing a file that moved, the Copilot file naming an index that
was renamed, a hook pointing at "§5" after `AGENTS.md` was renumbered: each
leaves a tool believing it has been told the rules. These guard the
hand-written layer around the generated context, and that `pf context refresh`
is the one-step fix for the generated layer.
"""

from __future__ import annotations

from pathlib import Path

from conftest import REPO_ROOT
from pf.agentcontext import ENTRY_POINTS, GENERATED, check, references, refresh, sections
from pf.memory import add


def test_the_entry_points_agree_in_this_repo() -> None:
    """Run `uv run pf context check` for the reason if this fails."""
    assert check(REPO_ROOT) == []


def test_every_generated_artefact_is_current_in_this_repo() -> None:
    """`refresh --dry-run` lists what a fresh regeneration would change; nothing may be stale."""
    stale = [str(p.relative_to(REPO_ROOT)) for p in refresh(REPO_ROOT, dry_run=True)]
    assert stale == [], f"run `uv run pf context refresh`: {stale}"


def test_agents_md_names_everything_the_check_relies_on() -> None:
    text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert {0, 1, 2, 3, 4, 5, 6, 7} <= sections(text), "the protocol's numbered sections are what pointers target"
    for f in (*ENTRY_POINTS, *GENERATED):
        if f != "AGENTS.md":
            assert f in text, f"AGENTS.md must name {f}"


def _conforming(tmp_path: Path) -> Path:
    """The smallest tree `check` accepts: every file present, every mention made."""
    root = tmp_path
    (root / "platform").mkdir()
    (root / "groups" / "g" / "projects" / "p").mkdir(parents=True)
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / "platform" / "toolkits" / "power-tools" / "hooks").mkdir(parents=True)
    for m in ("", "platform", "groups/g", "groups/g/projects/p"):
        d = root / m / ".memory" / "notes"
        d.mkdir(parents=True)
        (d / "README.md").write_text("x", encoding="utf-8")
    (root / "CLAUDE.md").write_text("router", encoding="utf-8")
    (root / "AGENTS.md").write_text(
        "# p\n\nCLAUDE.md GEMINI.md .github/copilot-instructions.md\n"
        ".memory/MEMORY.md docs/ARCHITECTURE.md platform/tests/README.md\n"
        "**Session** **Autonomous** **Inline** pf memory add pf context check\n"
        + "".join(f"## {n}. s\n" for n in range(8)),
        encoding="utf-8",
    )
    (root / "GEMINI.md").write_text("see §0\n\n@./CLAUDE.md\n\n@./AGENTS.md\n", encoding="utf-8")
    (root / ".github" / "copilot-instructions.md").write_text(
        "CLAUDE.md AGENTS.md .memory/MEMORY.md §3 §4 §5", encoding="utf-8"
    )
    (root / ".github" / "workflows" / "claude.yml").write_text("PF_AGENT: x\nAGENTS.md section 4", encoding="utf-8")
    (root / ".github" / "workflows" / "copilot-setup-steps.yml").write_text(
        "copilot-setup-steps:\n pf memory check", encoding="utf-8"
    )
    (root / "platform" / "toolkits" / "power-tools" / "hooks" / "session_start.sh").write_text(
        "AGENTS.md §5 pf memory show", encoding="utf-8"
    )
    return root


def test_a_conforming_tree_passes_and_each_drift_is_named(tmp_path: Path) -> None:
    root = _conforming(tmp_path)
    assert check(root) == []

    (root / "GEMINI.md").write_text("see §9\n\n@./CLAUDE.md\n\n@./AGENTS.md\n", encoding="utf-8")
    [problem] = check(root)
    assert "GEMINI.md" in problem and "§9" in problem and "renumbered" in problem

    (root / "GEMINI.md").write_text("@./CLAUDE.md\n", encoding="utf-8")
    [problem] = check(root)
    assert "GEMINI.md" in problem and "@./AGENTS.md" in problem

    (root / "GEMINI.md").unlink()
    [problem] = check(root)
    assert problem.startswith("GEMINI.md is missing")


def test_a_module_without_its_readme_is_named(tmp_path: Path) -> None:
    root = _conforming(tmp_path)
    (root / "groups" / "g" / ".memory" / "notes" / "README.md").unlink()
    [problem] = check(root)
    assert problem.startswith("groups/g:") and "pf context refresh" in problem


def test_section_references_are_read_in_both_spellings() -> None:
    assert references("see §0, § 3 and section 5; Section 12 too") == {0, 3, 5, 12}
    assert sections("## 0. a\n## 7. b\n### 9. not a section\n") == {0, 7}


def test_refresh_writes_the_missing_pieces_and_then_nothing(tmp_path: Path) -> None:
    """Dry run names what is stale; a real run writes exactly that; a second run is a no-op."""
    root = _conforming(tmp_path)
    (root / "groups" / "g" / ".memory" / "notes" / "README.md").unlink()
    add(root, "platform", "a-note", "one line", agent="t")
    (root / ".memory" / "MEMORY.md").unlink()
    would = {p.relative_to(root).as_posix() for p in refresh(root, dry_run=True)}
    assert would == {"groups/g/.memory/notes/README.md", ".memory/MEMORY.md"}
    assert not (root / ".memory" / "MEMORY.md").exists(), "dry run writes nothing"
    did = {p.relative_to(root).as_posix() for p in refresh(root)}
    assert did == would
    assert refresh(root, dry_run=True) == []
