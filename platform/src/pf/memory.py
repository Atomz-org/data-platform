"""Session memory — what an agent learned, written where the next agent will look.

A lesson that lives in one tool's private store is a lesson every other tool
pays for again. Claude Code keeps its own memory under `~/.claude/projects/`,
which no other tool can see; most tools have no memory of their own at all. So
the memory lives in the repository, as tracked markdown, in the module it is
about — and every tool is told the same thing by whichever file it reads
(`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md`):
read it before starting, add to it before finishing. Who wrote a note is
recorded on the note (`agent:`) — required, detected from the environment or
given with `--agent` — so the ledger says which tool learned what without
anyone trusting a filename.

Layout mirrors the repository's own structure, and so do the reading rules:

    .memory/notes/<lesson>.md                          repo-wide — CI, git, PRs, the session layer
    platform/.memory/notes/<lesson>.md                 shared engines — true of every project
    groups/<g>/.memory/notes/<lesson>.md               one family — shared by its sisters
    groups/<g>/projects/<p>/.memory/notes/<lesson>.md  one entity
    .memory/MEMORY.md                                  GENERATED — the index of all of the above

Which module a lesson belongs to follows the same rule as the code it is about:
true of every project → `platform/` (or root, if it is about git, CI or the
session rather than an engine); true of one family → the group; true of one
entity → the project. A project session reads root, platform, its group and
itself — never a sister — which is exactly the Read denylist its
`.claude/settings.json` already enforces, so the memory layout adds no new
boundary and crosses none.

This is deliberately *not* `decisions/loop-memory.yaml` (`pf loop memory`).
That file is a loop's memory of its own findings — suppress this, annotate
that — and it filters what reaches the ledger. This is a person's or agent's
memory of the repository: why something is the way it is, what a rebuild does
silently, which command costs a session if you get the order wrong. One
changes a loop's output; the other changes the next reader's first move.

One lesson per file. Frontmatter carries the one line the index shows, the
body says why and how to apply it:

    ---
    name: stale-manifest-trap
    description: pf kg build reads target/manifest.json and never reparses it just because a model changed
    type: project          # project | feedback | reference | user — same vocabulary as Claude's store
    status: active         # or resolved — kept for the record, marked so it is not acted on
    agent: claude-code     # who wrote it — detected (PF_AGENT, CLAUDECODE, GEMINI_CLI, GITHUB_ACTIONS) or --agent
    ---
    body

The index is generated, checked, and budgeted, for the same reasons the test
index is: an index that omits a note answers "does anyone know about this"
with confident silence, and an index that grows without bound stops being read.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

MEMORY_DIR = ".memory"
NOTES_DIR = "notes"
INDEX_NAME = "MEMORY.md"

TYPES = ("project", "feedback", "reference", "user")
STATUSES = ("active", "resolved")

#: Same shape of ceiling as the test index (`test_suite_index.py`): the point of
#: an index is to be read, and one that lists every lesson at length is the
#: thing it was meant to replace. When this binds, the answer is a per-module
#: rollup, not a bigger number.
#:
#: Raised 1600 → 2500 on 2026-09-26 (maintainer's call): twenty notes sat at
#: 1598, so every pull request that recorded a lesson — which the skills ask
#: for — failed the suite on `main`'s state rather than its own. The rollup
#: is still the answer when this binds again; the room is for landing notes.
INDEX_BUDGET = 2500

README_TEXT = """\
# Session memory

One lesson per file, one line in the frontmatter `description`, the why and
the how-to-apply in the body. Written mid-task by whichever agent learned it —
Claude Code, Copilot, a person — so the next session, whichever tool runs it,
does not pay for the same lesson twice.

    uv run pf memory show            # what applies here, one line each
    uv run pf memory show --full     # with bodies
    uv run pf memory add <module> <name> "<one line>" --body-file notes.md

`add` writes the file into the right module and regenerates `.memory/MEMORY.md`,
the index CI checks (`pf memory check`). Never hand-edit the index; edit the
note and run `pf memory index`.

Put a lesson here only if it is about *this* module. A lesson that is true of
every project belongs in `platform/.memory/notes/`; one about git, CI or the
session layer belongs at the repo root. A sister project's lessons are not
readable from here, by design.

Write it dense. The `description` is one keyword-rich line, not a sentence
with a preamble; the body is why and how-to-apply, and nothing else. A new
dependency or constraint you introduced is exactly what belongs here — say
what it rules out. What is *in progress* does not belong here: that is the
branch and its pull request.

Promotion into a `CLAUDE.md` (always loaded, budgeted) is a reviewed, human
step — that promotion is what makes the platform compound instead of
accumulating notes nobody reads.
"""


@dataclass(frozen=True)
class Note:
    module: str  # "root", "platform", "groups/<g>", "groups/<g>/projects/<p>"
    path: Path
    name: str
    description: str
    type: str
    status: str
    agent: str = ""  # who wrote it; "" when the note predates the field or nothing was detected

    @property
    def resolved(self) -> bool:
        return self.status == "resolved"


# ---------------------------------------------------------------- layout ---
def module_roots(root: Path) -> list[tuple[str, Path]]:
    """Every module that may hold memory, in the order the index lists them.

    Discovered from the tree rather than declared, so a new group or project
    is a memory module the moment it exists. `vendor/` is deliberately absent:
    it is read-only, and a lesson about an upstream belongs to the platform
    code that adopted it.
    """
    out: list[tuple[str, Path]] = [("root", root), ("platform", root / "platform")]
    gdir = root / "groups"
    if gdir.is_dir():
        for g in sorted(p for p in gdir.iterdir() if p.is_dir() and not p.name.startswith(".")):
            out.append((f"groups/{g.name}", g))
            pdir = g / "projects"
            if pdir.is_dir():
                for p in sorted(x for x in pdir.iterdir() if x.is_dir() and not x.name.startswith(".")):
                    out.append((f"groups/{g.name}/projects/{p.name}", p))
    return out


def module_path(root: Path, module: str) -> Path:
    for name, path in module_roots(root):
        if name == module:
            return path
    raise KeyError(f"no such module: {module!r} — one of {[m for m, _ in module_roots(root)]}")


def notes_dir(root: Path, module: str) -> Path:
    return module_path(root, module) / MEMORY_DIR / NOTES_DIR


def index_path(root: Path) -> Path:
    return root / MEMORY_DIR / INDEX_NAME


def module_for(root: Path, cwd: Path) -> str:
    """The module a working directory sits in — how `pf memory show` scopes
    itself the same way `pf.mcp.server.active_project` does."""
    try:
        rel = cwd.resolve().relative_to(root.resolve())
    except ValueError:
        return "root"
    parts = rel.parts
    if len(parts) >= 4 and parts[0] == "groups" and parts[2] == "projects":
        return f"groups/{parts[1]}/projects/{parts[3]}"
    if len(parts) >= 2 and parts[0] == "groups":
        return f"groups/{parts[1]}"
    if parts and parts[0] == "platform":
        return "platform"
    return "root"


def visible_from(module: str) -> list[str]:
    """What a session in `module` may read: root and platform always, its
    group if it has one, itself. Never a sister — same rule as the settings."""
    out = ["root", "platform"]
    if module.startswith("groups/"):
        parts = module.split("/")
        out.append(f"groups/{parts[1]}")
        if len(parts) == 4:
            out.append(module)
    return list(dict.fromkeys(out))


# ----------------------------------------------------------------- agent ---
#: One token, no whitespace or quotes: a name the index can print in a column.
#: `actions:copilot-swe-agent[bot]` is a valid one, so brackets are allowed.
_AGENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@\[\]-]*$")


def detect_agent() -> str:
    """Which tool is writing, from the environment. `PF_AGENT` when the operator
    says so, else the mark each tool leaves on the shells it spawns, else "".

    Recorded, not trusted: it is the ledger's *who* column, the same way a git
    author is, and it authorises nothing. A tool this does not know sets
    `PF_AGENT`; nothing here needs to change for a new model to be named.

    A person at a terminal is the one writer with no mark to leave, so an
    interactive stdin with nothing else set is recorded as `human`. Every
    agent tool drives its shell through pipes, so none of them can claim it.
    """
    env = os.environ
    explicit = env.get("PF_AGENT", "").strip()
    if explicit:
        return explicit
    if env.get("CLAUDECODE"):
        return "claude-code"
    if env.get("GEMINI_CLI"):
        return "gemini-cli"
    if env.get("GITHUB_ACTIONS"):
        actor = env.get("GITHUB_ACTOR", "").strip()
        return f"actions:{actor}" if actor else "actions"
    try:
        if sys.stdin.isatty():
            return "human"
    except (AttributeError, ValueError):
        pass
    return ""


# ----------------------------------------------------------------- notes ---
_FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_note(path: Path, module: str) -> Note:
    text = path.read_text(encoding="utf-8")
    meta: dict = {}
    m = _FRONT.match(text)
    if m:
        try:
            loaded = yaml.safe_load(m.group(1))
            if isinstance(loaded, dict):
                meta = loaded
        except yaml.YAMLError:
            meta = {}
    # Claude's own store nests `type` under `metadata:`; accept both so a note
    # copied verbatim from there is a valid note here.
    nested = meta.get("metadata") if isinstance(meta.get("metadata"), dict) else {}
    description = str(meta.get("description") or "").strip()
    if not description:
        body = text[m.end() :] if m else text
        first = next((ln.strip() for ln in body.splitlines() if ln.strip()), "")
        description = first.lstrip("#").strip()
    return Note(
        module=module,
        path=path,
        name=str(meta.get("name") or path.stem),
        description=description,
        type=str(meta.get("type") or nested.get("type") or "project"),
        status=str(meta.get("status") or "active"),
        agent=str(meta.get("agent") or nested.get("agent") or "").strip(),
    )


def scan(root: Path) -> list[Note]:
    """Every note in every module. README.md is the convention's own
    explanation, not a lesson, and is skipped."""
    out: list[Note] = []
    for module, mpath in module_roots(root):
        d = mpath / MEMORY_DIR / NOTES_DIR
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.md")):
            if p.name.lower() == "readme.md":
                continue
            out.append(parse_note(p, module))
    return out


def relevant(root: Path, module: str) -> list[Note]:
    allowed = set(visible_from(module))
    return [n for n in scan(root) if n.module in allowed]


def add(
    root: Path,
    module: str,
    name: str,
    description: str,
    *,
    body: str = "",
    type_: str = "project",
    status: str = "active",
    agent: str = "",
) -> Path:
    """Write one note and regenerate the index. Refuses a bad slug, an unknown
    type, or a name already taken — a second file with the same name is how a
    correction ends up living beside the mistake it corrects. `agent` is who
    is writing; callers pass `detect_agent()` unless the operator said."""
    if not _SLUG.match(name):
        raise ValueError(f"name must be a kebab-case slug: {name!r}")
    if not agent:
        raise ValueError(
            "say who is writing: --agent <name>, or export PF_AGENT=<name> once — "
            "nothing in this environment identifies the tool"
        )
    if not _AGENT.match(agent):
        raise ValueError(f"agent must be one token, no spaces or quotes: {agent!r}")
    if type_ not in TYPES:
        raise ValueError(f"type must be one of {TYPES}: {type_!r}")
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}: {status!r}")
    if not description.strip():
        raise ValueError("description is the one line the index shows; it cannot be empty")
    d = notes_dir(root, module)
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.md"
    if p.exists():
        raise FileExistsError(f"{p.relative_to(root)} exists — edit it, or pick another name")
    fm: dict[str, str] = {
        "name": name,
        "description": description.strip(),
        "type": type_,
        "status": status,
        "agent": agent,
    }
    front = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=1000)
    text = f"---\n{front}---\n\n{body.strip()}\n" if body.strip() else f"---\n{front}---\n"
    p.write_text(text, encoding="utf-8")
    write_index(root)
    return p


# ---------------------------------------------------------------- readme ---
def init_readmes(root: Path, *, modules: list[str] | None = None) -> list[Path]:
    """Put the convention's README into every module's notes dir that lacks one.

    Idempotent, and never overwrites: a module that rewrote its README to say
    something more specific keeps it. Creating the directory is what makes it
    exist in git — an empty `.memory/notes/` is invisible to a clone, and eleven
    projects had exactly that.
    """
    wrote: list[Path] = []
    for module, mpath in module_roots(root):
        if modules is not None and module not in modules:
            continue
        d = mpath / MEMORY_DIR / NOTES_DIR
        p = d / "README.md"
        if p.exists():
            continue
        d.mkdir(parents=True, exist_ok=True)
        p.write_text(README_TEXT, encoding="utf-8")
        wrote.append(p)
    return wrote


# ----------------------------------------------------------------- index ---
_GLOSS = {
    "root": "repo-wide — git, CI, pull requests, the session layer",
    "platform": "shared engines — true of every project",
}


def _gloss(module: str) -> str:
    if module in _GLOSS:
        return _GLOSS[module]
    parts = module.split("/")
    if len(parts) == 2:
        return "one family — shared by its sisters"
    return "one entity"


def render_index(notes: list[Note], root: Path) -> str:
    """The index, as markdown. Deterministic — it is compared byte for byte."""
    by_module: dict[str, list[Note]] = {}
    for n in notes:
        by_module.setdefault(n.module, []).append(n)
    order = [m for m, _ in module_roots(root)]
    modules_with = [m for m in order if m in by_module]
    active = sum(1 for n in notes if not n.resolved)
    resolved = len(notes) - active

    lines = [
        "# Memory — what agents have learned about this repository",
        "",
        "GENERATED by `pf memory index`. Do not hand-edit — `pf memory check` fails",
        "the build when this file and the notes disagree, and the notes win.",
        "",
        (
            f"{len(notes)} notes across {len(modules_with)} module(s) · {active} active"
            + (f", {resolved} resolved" if resolved else "")
            + " · `uv run pf memory show` for the ones that apply where you are"
        ),
        "",
        "A lesson is one file: frontmatter (`name`, `description`, `type`, `status`,",
        "`agent` — which tool wrote it) and a body saying why and how to apply it.",
        '`pf memory add <module> <name> "<one line>"` writes it into the right module',
        "and regenerates this index.",
        "Root and `platform/` apply everywhere; a group's notes apply to its sisters;",
        "a project's notes apply to it alone and are never read from a sister.",
        "",
    ]
    idx_dir = index_path(root).parent
    for module in modules_with:
        members = sorted(by_module[module], key=lambda n: n.name)
        rel_dir = os.path.relpath(notes_dir(root, module), idx_dir).replace(os.sep, "/")
        heading = "Repository-wide" if module == "root" else f"`{module}/`"
        lines += [
            f"## {heading} — {_gloss(module)}",
            "",
            f"*{len(members)} note(s) · `{rel_dir}/`*",
            "",
            "| note | one line | by |",
            "|---|---|---|",
        ]
        for n in members:
            link = os.path.relpath(n.path, idx_dir).replace(os.sep, "/")
            desc = n.description.replace("|", "\\|")
            if n.resolved:
                desc = f"*(resolved)* {desc}"
            lines.append(f"| [{n.name}]({link}) | {desc} | {n.agent or '—'} |")
        lines.append("")

    lines += [
        "## Keeping this true",
        "",
        "```bash",
        "uv run pf memory index     # regenerate this file from the notes",
        "uv run pf memory check     # fail if it and the notes disagree",
        "uv run pf memory log       # who added what, when — from git, on demand",
        "```",
        "",
        "`pf memory check` runs in `platform-tests.yml` and in the suite, so a note",
        "cannot land without its line here — and this file cannot claim a note that",
        "no longer exists.",
        "",
    ]
    return "\n".join(lines)


def write_index(root: Path) -> tuple[Path, bool]:
    out = index_path(root)
    content = render_index(scan(root), root)
    changed = not out.exists() or out.read_text(encoding="utf-8") != content
    if changed:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
    return out, changed


def drift(root: Path) -> str:
    """Empty when the committed index matches the notes; otherwise why not."""
    out = index_path(root)
    notes = scan(root)
    if not out.exists():
        if not notes:
            return ""
        return f"{out.relative_to(root)} is missing and {len(notes)} note(s) exist — run `pf memory index`"
    expected = render_index(notes, root)
    if out.read_text(encoding="utf-8") != expected:
        return f"{out.relative_to(root)} is stale — run `pf memory index`"
    for n in notes:
        if not n.description:
            return f"{n.path.relative_to(root)} has no description line to index"
        if not _SLUG.match(n.path.stem):
            return f"{n.path.relative_to(root)}: note filenames are kebab-case slugs"
        if n.type not in TYPES:
            return f"{n.path.relative_to(root)}: type {n.type!r} is not one of {TYPES}"
        if n.status not in STATUSES:
            return f"{n.path.relative_to(root)}: status {n.status!r} is not one of {STATUSES}"
        if not n.agent:
            return f"{n.path.relative_to(root)}: no `agent:` line — who wrote it? add `agent: <name>`"
        if not _AGENT.match(n.agent):
            return f"{n.path.relative_to(root)}: agent {n.agent!r} must be one token, no spaces or quotes"
    stray = _stray_notes(root)
    if stray:
        return (
            f"{stray[0]} is a memory note outside every module — move it under "
            f"the root, platform, a group or a project `.memory/notes/`"
        )
    return ""


def _stray_notes(root: Path) -> list[str]:
    """`.memory/notes/*.md` anywhere the index does not look. A lesson written
    into a directory nobody indexes is the silent failure this check exists for."""
    known = {notes_dir(root, m).resolve() for m, _ in module_roots(root)}
    skip = {"vendor", ".venv", "node_modules", ".git", "okf"}
    out: list[str] = []
    for d in root.rglob(NOTES_DIR):
        if d.parent.name != MEMORY_DIR or not d.is_dir():
            continue
        if any(part in skip for part in d.relative_to(root).parts):
            continue
        if d.resolve() in known:
            continue
        for p in sorted(d.glob("*.md")):
            if p.name.lower() != "readme.md":
                out.append(str(p.relative_to(root)))
    return out


def log(root: Path, limit: int = 20) -> str:
    """Who added or changed what, from git — on demand rather than stored, so
    the index stays a deterministic projection of the notes."""
    r = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "log",
            f"-{limit}",
            "--date=short",
            "--format=%h %ad %an%x09%s",
            "--",
            f"{MEMORY_DIR}/",
            f"*/{MEMORY_DIR}/*",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return r.stdout.strip()


def stamp() -> str:
    return datetime.now(UTC).date().isoformat()
