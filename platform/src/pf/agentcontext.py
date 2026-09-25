"""Agent context — the files every tool reads before its first edit, checked as one.

Three tools, three entry points, one protocol:

    CLAUDE.md                          Claude Code's router (budgeted, `pf tokens`)
    AGENTS.md                          the protocol, per execution scope, for any model
    GEMINI.md                          Gemini's entry point — imports the two above
    .github/copilot-instructions.md    Copilot's entry point — points at the two above

and four pieces of generated context they all send the reader to:

    .memory/MEMORY.md                  `pf memory index`
    platform/tests/README.md           `pf test index`
    docs/ARCHITECTURE.md               `pf arch build`
    docs/ONBOARDING.md                 `pf guide build` (with its HTML twin)

and the per-harness config layer — Codex, Cursor, Gemini, VS Code, OpenCode —
rendered from `.mcp.json` by `pf.harness`, so a tool that is not Claude Code
still reaches the graph and knows exactly which gate applies to it
(`docs/HARNESSES.md`). Those are generated too, and checked here for the same
reason: a stale `.codex/config.toml` is a Codex session with no graph and no
error.

Each generated piece already has its own drift check. What nothing checked was
the hand-written layer *around* them: that `GEMINI.md` still imports the
protocol, that the Copilot file still names the memory index, that a pointer
like "§5" in the hook still means a section that exists after `AGENTS.md` is
renumbered, that every module has the README that makes its `.memory/notes/`
exist in git. Those are the drifts a renumbering or a rename causes silently,
and a pointer file that points at nothing is worse than none — the tool that
reads it believes it has been told.

`check` is those rules, plus the code-graph wiring (`pf.codegraph`), which
fails the same way: a missing marker directory does not error, it silently
widens the graph from `platform/` to every sister project. `refresh`
regenerates the generated pieces in one step, so the fix for "stale" is one
command whichever piece went stale. Token budgets are deliberately not here:
`pf tokens` owns them, and an over-budget card is a decision for a person,
not something a refresh can make.

`refresh` also regenerates what each project projects from its committed
graph — `mdl/mdl.json` and the OKF bundles — because the workflow checks them
too, and a refresh that fixes some of what the check names leaves the author
to find the rest one red run at a time. Projects are discovered on every run,
so a group, a project or a feature added or removed needs no edit here.

The `agent-context` workflow runs `check` and the drift checks on every pull
request — no path filter, because the point is *every* PR — and its `refresh`
job commits exactly the paths `refresh` reports.
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
#: drift check; `refresh` regenerates all four.
GENERATED: tuple[str, ...] = (
    ".memory/MEMORY.md",
    "docs/ARCHITECTURE.md",
    "docs/ONBOARDING.md",
    "platform/tests/README.md",
)

#: (file, what it must still say, why). A plain substring test on purpose:
#: the failure mode is a rename or a deletion, not a subtle rewording.
_MENTIONS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("AGENTS.md", ("CLAUDE.md", "GEMINI.md", ".github/copilot-instructions.md"), "every entry point"),
    ("AGENTS.md", GENERATED, "every generated context artefact"),
    ("AGENTS.md", ("docs/HARNESSES.md",), "the harness scorecard — where enforcement is a hook and where it is a rule"),
    ("AGENTS.md", ("HARNESS.md", "pf harness"), "the per-scope harness maps and the verb that regenerates them"),
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

    # The other graph an agent is told to ask. Checked here so one command
    # covers every piece of shared context, rather than each tool owning a
    # check nobody remembers to run.
    from pf import codegraph

    problems.extend(codegraph.check(root))

    # The per-harness configs, for the same reason: `pf context check` is the
    # one command, and a Codex config that no longer lists the `pf` server is
    # a drift that fails by *succeeding* — the session starts, with no graph.
    from pf import harness

    problems.extend(harness.check(root))
    return problems


def projects(root: str | Path) -> list[tuple[str, str, Path]]:
    """Every `(group, project, directory)` under `groups/`, discovered, never listed.

    The same walk as `pf.cli.all_projects`, from an explicit root: a group or a
    project added or removed changes what `refresh` covers without an edit here.
    """
    gdir = Path(root) / "groups"
    out: list[tuple[str, str, Path]] = []
    if not gdir.is_dir():
        return out
    for g in sorted(x for x in gdir.iterdir() if x.is_dir() and not x.name.startswith(".")):
        pdir = g / "projects"
        if pdir.is_dir():
            found = sorted(x for x in pdir.iterdir() if x.is_dir() and not x.name.startswith("."))
            out.extend((g.name, p.name, p) for p in found)
    return out


def refresh(root: str | Path, *, dry_run: bool = False, notes: list[str] | None = None) -> list[Path]:
    """Regenerate every generated piece of context and return what changed.

    With `dry_run`, nothing is written and the return value is what *would*
    change — how CI tells "stale" from "current" without touching the tree.
    Pieces whose inputs are not present in this tree are skipped, so a bare
    skeleton (a test's, a new clone's) refreshes what it has and no more.

    Everything the `agent-context` workflow compares is regenerated here, in
    the order each reads the last: what each project projects from its
    committed graph (the MDL manifest, then the OKF bundle, which reads it),
    then the repo-wide pieces that count across projects, and the harness maps
    last because they read all of it. So "stale" has one fix, whichever check
    said so and whichever project, feature or group the change added or
    removed — projects are discovered, never listed.

    The graph itself is not rebuilt. `kg/graph.json` is built from a dbt
    parse and, where there is one, the warehouse, so a rebuild on a machine
    without the warehouse is a *poorer* graph rather than a fresher one, and
    everything projected from it would lose pages with it. `pf kg build` owns
    the graph; this regenerates what is derived from the committed one, which
    is exactly what the checks compare. Each project's `kg/architecture.md` is
    left to `pf arch` for the same reason: it counts from `kg/graph.duckdb`,
    which nothing commits.

    `notes`, when given, collects what could not be refreshed in this tree and
    why — a piece whose inputs are absent is skipped, never failed silently.
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

    def remove(path: Path) -> None:
        changed.append(path)
        if not dry_run:
            path.unlink()

    targets = projects(root)

    # What each project projects from its committed graph. The same builder
    # the check compares against — `tracked=True`, as `pf semantic mdl --check`
    # uses — so a refresh cannot write what the check would then call stale.
    if targets:
        import json

        from pf.projections import mdl

        for g, p, d in targets:
            if (d / "kg" / "graph.json").is_file():
                built = mdl.build_manifest(d, g, p, tracked=True)
                write(d / "mdl" / "mdl.json", json.dumps(built, indent=2) + "\n")

    # The OKF bundles, every tier `pf tool okf check --all` judges: the
    # platform's, each group that has projects, each project. A page the layer
    # no longer has is removed, exactly as `pf tool okf build` does.
    if targets and (root / "platform" / "src" / "pf").is_dir():
        from pf.projections import okf

        def bundle(out: Path, files: dict[str, str]) -> None:
            for rel, text in files.items():
                write(out / rel, text)
            for sub in okf.MANAGED_DIRS:
                d = out / sub
                for page in sorted(d.glob("*.md")) if d.is_dir() else []:
                    if f"{sub}/{page.name}" not in files:
                        remove(page)

        # The bundle's schema is the vendored weaver's; without the submodule
        # there is nothing to render against. Said, not swallowed — a refresh
        # that quietly did less than the check compares is the gap this closes.
        try:
            bundle(root / okf.PLATFORM_REL, okf.build_platform(root))
            for g in sorted({g for g, _, _ in targets}):
                bundle(okf.group_bundle(root, g), okf.build_group(root, g))
            for g, p, d in targets:
                bundle(d / okf.OKF_REL, okf.build_project(root, g, p))
        except okf.NotVendored as exc:
            if notes is not None:
                notes.append(f"OKF bundles not refreshed: {exc}")

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
        from pf import archmap, guide

        write(archmap.doc_path(root), archmap.render(archmap.gather(root)))
        # The guide's HTML twin is regenerated with it: one page, two renderings,
        # and a check that fails on either.
        g = guide.gather(root)
        write(guide.md_path(root), guide.render_markdown(g))
        write(guide.html_path(root), guide.render_html(g))

    # The harness configs need only `.mcp.json`, so they are refreshed in any
    # tree that has one — including a bare test skeleton, which is how the
    # conforming-tree tests get theirs.
    if (root / ".mcp.json").is_file():
        from pf import harness

        for rel, content in harness.targets(root).items():
            write(root / rel, content)

    # The per-scope harness maps — one per group, per project and per report.
    # Read from each scope's settings, the gate, the hooks, its workflow and
    # its loops, which is why a refresh is the fix when any of those move.
    if (root / "groups").is_dir():
        from pf import harnessmap

        for scope in harnessmap.scopes(root):
            write(scope.path(root), scope.render(root))

    return changed
