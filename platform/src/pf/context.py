"""The always-on context layer — what every agent knows before it does anything.

An agent that does not know a capability exists solves the problem the expensive
way. It greps for a dashboard convention that is written down, writes SQL for a
metric that is already defined, or edits a compiled artefact and spends a turn
discovering the gate refuses it. Every one of those is a token cost paid *because*
context was missing, and each costs far more than the context would have.

So this layer is a token argument, not a documentation one. The 29 skills under
`platform/toolkits/` are ~8,600 tokens if an agent reads them to find out what
exists. The generated index below is a few hundred, sits behind the prompt-cache
breakpoint at ~0.1x on reads, and answers the same question.

Two artefacts, split by what varies:

  * **`platform/toolkits/TOOLKITS.md`** — one index of every toolkit and skill.
    Identical for every project, so it is generated once and cached once.
  * **`groups/<g>/projects/<p>/kg/tools_card.md`** — only what differs per
    project: the capabilities this project actually has, and their rules.

Both are **generated**. A hand-maintained index is a stale index: it agrees with
the code on the day it is written and silently diverges after, which is worse
than no index because it is believed. Toolkit entries come from each skill's own
frontmatter and each toolkit's `CONTEXT.md`; capability entries come from the
`Capability` declaration. Nothing is written twice.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pf.capabilities import CAPABILITIES, Capability
from pf.scaffold.generator import render

# Budgets. Enforced by `pf tokens`, which fails rather than warns: the always-on
# tier is the one that silently inflates every session, and a budget nobody
# enforces is a comment.
TOOLKIT_INDEX_BUDGET = 1300
TOOLS_CARD_BUDGET = 400

TOOLKIT_INDEX = "platform/toolkits/TOOLKITS.md"
TOOLS_CARD = "kg/tools_card.md"

_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---", re.DOTALL)


# ------------------------------------------------------------- discovery ----
@dataclass(frozen=True)
class Skill:
    name: str
    description: str


@dataclass(frozen=True)
class Toolkit:
    """One toolkit, as the index sees it."""

    name: str
    when: str = ""
    rules: tuple[str, ...] = ()
    skills: tuple[Skill, ...] = field(default_factory=tuple)


class MalformedFrontmatter(ValueError):
    """A CONTEXT.md or SKILL.md whose frontmatter does not parse."""


def _frontmatter(path: Path, strict: bool = False) -> dict:
    """Parse a markdown file's YAML frontmatter.

    Unparseable frontmatter is the one failure worth being loud about. It does
    not look like an error — the file is there, the index still renders, and the
    toolkit's rules have simply vanished from every agent's context. That is a
    rule silently switched off, which is strictly worse than a missing file.

    So rendering tolerates it (a broken toolkit must not stop the index every
    other toolkit depends on), and `problems()` reports it. One YAML gotcha
    causes most of these: a list entry beginning with a double quote parses as a
    quoted scalar followed by junk.
    """
    if not path.exists():
        return {}
    m = _FRONTMATTER.match(path.read_text())
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as exc:
        if strict:
            raise MalformedFrontmatter(f"{path}: {exc}") from exc
        return {}


def problems(root: Path) -> list[str]:
    """Frontmatter that does not parse, and so is silently contributing nothing."""
    found: list[str] = []
    tdir = root / "platform" / "toolkits"
    if not tdir.exists():
        return found
    for path in sorted([*tdir.glob("*/CONTEXT.md"), *tdir.glob("*/skills/*/SKILL.md")]):
        try:
            _frontmatter(path, strict=True)
        except MalformedFrontmatter as exc:
            found.append(str(exc))
    return found


def load_toolkits(root: Path) -> list[Toolkit]:
    """Every toolkit, with its skills, read from their own frontmatter."""
    tdir = root / "platform" / "toolkits"
    if not tdir.exists():
        return []

    out: list[Toolkit] = []
    for d in sorted(x for x in tdir.iterdir() if x.is_dir()):
        meta = _frontmatter(d / "CONTEXT.md")
        rules = meta.get("rules") or []
        skills = tuple(
            Skill(name=fm.get("name", s.parent.name),
                  description=str(fm.get("description", "")).strip())
            for s in sorted((d / "skills").glob("*/SKILL.md"))
            if (fm := _frontmatter(s))
        )
        if not skills and not meta:
            continue  # an empty directory is not a toolkit
        out.append(Toolkit(
            name=d.name,
            when=str(meta.get("when", "")).strip(),
            rules=tuple(str(r).strip() for r in rules if str(r).strip()),
            skills=skills,
        ))
    return out


def applied_capabilities(root: Path, group: str, project: str) -> list[Capability]:
    """Which capabilities this project actually has.

    Derived from each capability's own `files` declaration rather than from a
    manifest. A manifest would be a second source of truth that can disagree with
    the filesystem, and the disagreement would surface as an agent being told
    about a capability whose files were never written.
    """
    pdir = root / "groups" / group / "projects" / project
    ctx = {"group": group, "project": project, "module": project.replace("-", "_")}

    out: list[Capability] = []
    for cap in CAPABILITIES.values():
        if not cap.files:
            continue
        # `.github/**` belongs to the repository, everything else to the project
        # — the same split `pf.capabilities.apply` writes them with.
        present = all(
            ((root if (rel := render(f, ctx)).startswith(".github/") else pdir) / rel).exists()
            for f in cap.files
        )
        if present:
            out.append(cap)
    return out


# --------------------------------------------------------------- rendering --
def render_toolkit_index(root: Path) -> str:
    """The platform-wide index: what exists, when to reach for it, what is forbidden.

    Deliberately carries skill *names* and not their descriptions. The full
    description already sits in each `SKILL.md`, which is loaded when the skill is
    invoked — repeating all 29 of them here costs ~800 always-on tokens to
    duplicate text the agent gets anyway at the moment it becomes relevant.

    What cannot be discovered that way, and so has to be here, is the routing
    signal (which toolkit, when) and the rules — a rule is only useful *before*
    the mistake, so it has to be in context ahead of the file that would have
    taught it.
    """
    toolkits = load_toolkits(root)
    lines = [
        "<!-- GENERATED by `pf context build`. Edit a toolkit's CONTEXT.md or a",
        "     skill's frontmatter, never this file. -->",
        "# Toolkits — what exists, and the rules for using it",
        "",
        "Skills are invoked by name; each one's own description is in its SKILL.md.",
        "Precedence between toolkits is in `ROUTING.md`.",
        "",
    ]

    for tk in toolkits:
        head = f"## {tk.name}"
        if tk.when:
            head += f" — {tk.when}"
        lines.append(head)
        if tk.skills:
            lines.append("  " + "  ".join(f"`{s.name}`" for s in tk.skills))
        lines += [f"  - {r}" for r in tk.rules]
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_tools_card(root: Path, group: str, project: str) -> str:
    """The per-project card: only what differs between projects."""
    caps = applied_capabilities(root, group, project)
    lines = [
        "<!-- GENERATED by `pf context build`. Edit the Capability declaration,",
        "     never this file. -->",
        f"# Capabilities — {group}/{project}",
        "",
    ]

    if not caps:
        lines += [
            "None enabled. `pf capabilities` lists what is available; add one with",
            f"`pf capability-add <name> {group} {project}`.",
        ]
        return "\n".join(lines) + "\n"

    for cap in caps:
        lines.append(f"## {cap.name}")
        lines.append(cap.context or cap.description)
        if cap.rules:
            lines += [f"- {r}" for r in cap.rules]
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ------------------------------------------------------------------ build ---
def build(root: Path, group: str = "", project: str = "") -> list[Path]:
    """Write the index, and one project's card when named. Returns what changed.

    Idempotent, so it is safe as a bootstrap step and safe to run in a loop over
    every project.
    """
    written: list[Path] = []

    index = root / TOOLKIT_INDEX
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(render_toolkit_index(root))
    written.append(index)

    if group and project:
        card = root / "groups" / group / "projects" / project / TOOLS_CARD
        card.parent.mkdir(parents=True, exist_ok=True)
        card.write_text(render_tools_card(root, group, project))
        written.append(card)

    return written


def is_stale(root: Path, group: str, project: str) -> bool:
    """Whether either artefact disagrees with what it is generated from.

    Checked by `pf check` for the same reason tracked-artefact drift is: a
    generated file that has silently stopped matching its source is believed by
    every agent that reads it.
    """
    index = root / TOOLKIT_INDEX
    if not index.exists() or index.read_text() != render_toolkit_index(root):
        return True
    card = root / "groups" / group / "projects" / project / TOOLS_CARD
    return not card.exists() or card.read_text() != render_tools_card(root, group, project)
