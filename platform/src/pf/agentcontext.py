"""Agent context — the files every tool reads before its first edit, checked as one.

Three tools, three entry points, one protocol:

    CLAUDE.md                          Claude Code's router (budgeted, `pf tokens`)
    AGENTS.md                          the protocol, per execution scope, for any model
    GEMINI.md                          Gemini's entry point — imports the two above
    .github/copilot-instructions.md    Copilot's entry point — points at the two above

and three pieces of generated context they all send the reader to:

    .memory/MEMORY.md                  `pf memory index`
    platform/tests/README.md           `pf test index`
    docs/ARCHITECTURE.md               `pf arch build`

Each generated piece already has its own drift check. What nothing checked was
the hand-written layer *around* them: that `GEMINI.md` still imports the
protocol, that the Copilot file still names the memory index, that a pointer
like "§5" in the hook still means a section that exists after `AGENTS.md` is
renumbered, that every module has the README that makes its `.memory/notes/`
exist in git. Those are the drifts a renumbering or a rename causes silently,
and a pointer file that points at nothing is worse than none — the tool that
reads it believes it has been told.

`check` is those rules. `refresh` regenerates the generated pieces in one step,
so the fix for "stale" is one command whichever piece went stale. Token budgets
are deliberately not here: `pf tokens` owns them, and an over-budget card is a
decision for a person, not something a refresh can make.

The `agent-context` workflow runs `check` and the three drift checks on every
pull request — no path filter, because the point is *every* PR.
"""

from __future__ import annotations

import re
from pathlib import Path

#: The file each tool reads first. Missing one means that tool works blind.
ENTRY_POINTS: tuple[str, ...] = (
    "CLAUDE.md",
    "AGENTS.md",
    "GEMINI.md",
    ".github/copilot-instructions.md",
)

#: Not entry points, but what makes the protocol true at runtime.
SUPPORTING: tuple[str, ...] = (
    ".github/workflows/claude.yml",
    ".github/workflows/copilot-setup-steps.yml",
    "platform/toolkits/power-tools/hooks/session_start.sh",
)

#: Generated context the entry points send a reader to. Each has its own
#: drift check; `refresh` regenerates all three.
GENERATED: tuple[str, ...] = (
    ".memory/MEMORY.md",
    "docs/ARCHITECTURE.md",
    "platform/tests/README.md",
)

#: (file, what it must still say, why). A plain substring test on purpose:
#: the failure mode is a rename or a deletion, not a subtle rewording.
_MENTIONS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("AGENTS.md", ("CLAUDE.md", "GEMINI.md", ".github/copilot-instructions.md"), "every entry point"),
    ("AGENTS.md", GENERATED, "every generated context artefact"),
    ("AGENTS.md", ("**Session**", "**Autonomous**", "**Inline**"), "the three execution scopes"),
    ("AGENTS.md", ("pf memory add", "pf context check"), "the write protocol and this check"),
    ("GEMINI.md", ("@./CLAUDE.md", "@./AGENTS.md"), "the imports of the router and the protocol"),
    (
        ".github/copilot-instructions.md",
        ("CLAUDE.md", "AGENTS.md", ".memory/MEMORY.md"),
        "the router, the protocol and the memory index",
    ),
    (
        "platform/toolkits/power-tools/hooks/session_start.sh",
        ("AGENTS.md", "pf memory show"),
        "the protocol and the memory a Claude session is told about on turn one",
    ),
    (".github/workflows/claude.yml", ("PF_AGENT:", "AGENTS.md"), "its agent name and the protocol"),
    (
        ".github/workflows/copilot-setup-steps.yml",
        ("copilot-setup-steps:", "pf memory check"),
        "the job name GitHub requires and the memory check",
    ),
)

#: Files that point into AGENTS.md by section number.
_POINTERS: tuple[str, ...] = (
    "AGENTS.md",
    "GEMINI.md",
    ".github/copilot-instructions.md",
    "platform/toolkits/power-tools/hooks/session_start.sh",
    ".github/workflows/claude.yml",
)
_SECTION = re.compile(r"^## (\d+)\.", re.MULTILINE)
_REF = re.compile(r"§\s?(\d+)|\bsection (\d+)\b", re.IGNORECASE)


def sections(protocol_text: str) -> set[int]:
    return {int(n) for n in _SECTION.findall(protocol_text)}


def references(text: str) -> set[int]:
    return {int(a or b) for a, b in _REF.findall(text)}


def check(root: str | Path) -> list[str]:
    """Every way the entry points can disagree, as one line each with the fix.
    Empty means they agree."""
    root = Path(root)
    problems: list[str] = []

    missing = [p for p in (*ENTRY_POINTS, *SUPPORTING) if not (root / p).exists()]
    for p in missing:
        problems.append(f"{p} is missing — the tool that reads it works blind; restore it from git")
    if missing:
        return problems

    for file, needles, why in _MENTIONS:
        text = (root / file).read_text(encoding="utf-8")
        absent = [n for n in needles if n not in text]
        if absent:
            problems.append(f"{file} no longer names {absent} — it must name {why}")

    known = sections((root / "AGENTS.md").read_text(encoding="utf-8"))
    for file in _POINTERS:
        dangling = sorted(references((root / file).read_text(encoding="utf-8")) - known)
        if dangling:
            problems.append(
                f"{file} points at AGENTS.md §{', §'.join(map(str, dangling))}, which does not exist — "
                f"AGENTS.md was renumbered; fix the pointer"
            )

    from pf.memory import module_roots, notes_dir

    for module, _ in module_roots(root):
        if not (notes_dir(root, module) / "README.md").exists():
            problems.append(
                f"{module}: .memory/notes/README.md is missing — the directory is invisible to a clone "
                f"without it; run `pf memory init` or `pf context refresh`"
            )
    return problems


def refresh(root: str | Path, *, dry_run: bool = False) -> list[Path]:
    """Regenerate every generated piece of context and return what changed.

    With `dry_run`, nothing is written and the return value is what *would*
    change — how CI tells "stale" from "current" without touching the tree.
    Pieces whose inputs are not present in this tree are skipped, so a bare
    skeleton (a test's, a new clone's) refreshes what it has and no more.
    """
    root = Path(root)
    changed: list[Path] = []

    def write(path: Path, content: str) -> None:
        if path.exists() and path.read_text(encoding="utf-8") == content:
            return
        changed.append(path)
        if not dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    from pf import memory

    for module, _ in memory.module_roots(root):
        readme = memory.notes_dir(root, module) / "README.md"
        if not readme.exists():
            write(readme, memory.README_TEXT)
    write(memory.index_path(root), memory.render_index(memory.scan(root), root))

    tests = root / "platform" / "tests"
    if tests.is_dir():
        from pf import testmap

        write(testmap.index_path(tests), testmap.render_index(testmap.scan(tests)))

    if (root / "docs").is_dir() and (root / "platform" / "src" / "pf").is_dir():
        from pf import archmap

        write(archmap.doc_path(root), archmap.render(archmap.gather(root)))

    return changed
