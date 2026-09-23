"""The onboarding guide, drawn from the repository.

`docs/ONBOARDING.md` and `docs/onboarding.html` are what a person new to this
repository reads first: the three tiers and who owns each, how one company's
data moves from a source to a dashboard, and what to run, in what order, to
bring a new company in. A guide like that is stale the day it is written, and a
stale one is worse than none: it sends a newcomer confidently to a command that
was renamed or a step that no longer exists.

So it is generated, on the same terms as `docs/ARCHITECTURE.md`. The prose is
a template; every group, project, count, command, capability, bootstrap step,
loop and ladder stage in it is read from the thing it describes, and
`pf guide check` fails the build when the committed copy and the repository
disagree. `pf context refresh` regenerates it with the other generated context,
and the `agent-context` workflow checks it on every pull request, with no path
filter, because a pull request that renames a command is exactly the one that
makes this page lie.

Two renderings from one document model. The Markdown is for GitHub and for an
agent reading `docs/`; the HTML is the same page as a standalone file, in the
house style of `docs/commodity-end-to-end.html`, so it can be published where a
newcomer will actually open it. Neither carries a date or a commit: the files
are compared byte for byte, and a timestamp would make every commit a stale one.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from pathlib import Path

from pf.archmap import Facts
from pf.archmap import gather as gather_facts

#: The only hosts the HTML may reference. Scripts are not needed at all, and a
#: page that loads one from anywhere else renders blank where it is published.
EXTERNAL_HOSTS = frozenset({"fonts.googleapis.com", "fonts.gstatic.com"})

TITLE = "Onboarding a Company"


# --------------------------------------------------------------- gather -----
@dataclass(frozen=True)
class ProjectRow:
    name: str
    tables: int
    models: int
    metrics: int
    exposures: int

    @property
    def reading(self) -> str:
        """What the counts mean for someone deciding where to look first."""
        if self.tables and self.models and self.metrics:
            return "sources, models and metrics"
        if self.models and not self.tables:
            return "models only, nothing ingested yet"
        if self.models:
            return "sources and models, no metric yet"
        return "empty scaffold"


@dataclass(frozen=True)
class GroupRow:
    name: str
    display_name: str
    domain: str
    lifecycle: str
    projects: tuple[ProjectRow, ...]


@dataclass
class Guide:
    """Everything the guide asserts, gathered once."""

    facts: Facts = field(default_factory=Facts)
    groups: list[GroupRow] = field(default_factory=list)
    steps: list[tuple[str, str]] = field(default_factory=list)
    domains: list[tuple[str, list[str]]] = field(default_factory=list)
    commands: list[tuple[str, str]] = field(default_factory=list)
    command_groups: list[tuple[str, str]] = field(default_factory=list)
    loops: list[tuple[str, str, str, str]] = field(default_factory=list)
    stages: list[tuple[str, str, str]] = field(default_factory=list)
    ci_jobs: list[str] = field(default_factory=list)
    docs: list[tuple[str, str]] = field(default_factory=list)


def _first_line(text: str | None) -> str:
    for line in (text or "").strip().splitlines():
        if line.strip():
            return line.strip()
    return ""


def gather(root: str | Path) -> Guide:
    """Read the repository. The prose is fixed; every fact in it is counted."""
    r = Path(root)
    g = Guide(facts=gather_facts(r))

    for name, projects in g.facts.groups.items():
        display, domain, lifecycle = name, "", ""
        try:
            from pf import groups as manifests

            if manifests.exists(r, name):
                m = manifests.load(r, name)
                display, domain, lifecycle = m.display_name or name, m.domain, m.lifecycle
        except Exception:  # noqa: BLE001 — a malformed manifest must not stop the guide
            pass
        rows = []
        for p in projects:
            c = g.facts.project_shape.get(f"{name}/{p}", {})
            rows.append(ProjectRow(p, c.get("Table", 0), c.get("Model", 0), c.get("Metric", 0), c.get("Exposure", 0)))
        g.groups.append(GroupRow(name, display, domain, lifecycle, tuple(rows)))

    try:
        from pf.scaffold.bootstrap import STEPS

        g.steps = [(s.name, s.why) for s in STEPS]
    except Exception:  # noqa: BLE001
        pass

    try:
        from pf.scaffold.generator import DEFAULT_CLASSES

        g.domains = sorted((d, list(c)) for d, c in DEFAULT_CLASSES.items())
    except Exception:  # noqa: BLE001
        pass

    try:
        from pf.cli import app

        cmds = []
        for c in app.registered_commands:
            name = c.name or c.callback.__name__.replace("_", "-")
            cmds.append((name, _first_line(c.help or c.callback.__doc__)))
        g.commands = sorted(cmds)
        grps = []
        for t in app.registered_groups:
            name = t.name or t.typer_instance.info.name or ""
            grps.append((name, _first_line(t.typer_instance.info.help)))
        g.command_groups = sorted(grps)
    except Exception:  # noqa: BLE001
        pass

    try:
        from pf.loops.registry import SPECS

        g.loops = sorted((s.name, s.autonomy, s.cadence, s.description) for s in SPECS.values())
    except Exception:  # noqa: BLE001
        pass

    try:
        from pf.onboard.ladder import STAGES

        g.stages = [(s.name, s.title, s.subject) for s in STAGES]
    except Exception:  # noqa: BLE001
        pass

    try:
        from pf.capabilities import CAPABILITIES

        g.ci_jobs = sorted({j for c in CAPABILITIES.values() for j in (c.ci_jobs or {})})
    except Exception:  # noqa: BLE001
        pass

    ddir = r / "docs"
    if ddir.is_dir():
        for p in sorted(ddir.glob("*.md")):
            if p.name == md_path(r).name:
                continue
            title = ""
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            g.docs.append((p.name, title))
    return g


# ------------------------------------------------------------- document -----
# One document model, two renderers. A block is a tuple whose first element
# names its kind; the renderers agree on the kinds and nothing else.

Block = tuple


def _flow() -> list[tuple[str, str, list[str], str]]:
    """One company's data, stage by stage: (name, where, what lives there, the rule on the hop out)."""
    return [
        (
            "Extract",
            "src/<module>/sources/",
            ["dlt @resource", "annotate(...)"],
            "**dlt lands raw only.** Never transform in a source; never join here.",
        ),
        (
            "Contract",
            "contracts/annotations.yaml",
            ["concept", "roles", "links", "grain"],
            (
                "Exported from the `annotate` calls by `pf seed`. Drives staging, PII policy, monitors, "
                "metric candidates and graph edges."
            ),
        ),
        (
            "Raw",
            "data/<project>.duckdb",
            ["one dataset per source", "types frozen", "row counts read back"],
            "**One row in, one row out.** `pf gen-staging` writes staging from the contract and cleans only.",
        ),
        (
            "Staging",
            "transform/models/staging/",
            ["stg_<source>__<table>.sql", "generated"],
            "No joins and no hand edits: the next `pf gen-staging` would discard them.",
        ),
        (
            "Intermediate",
            "transform/models/intermediate/",
            ["int_*.sql", "hand-written"],
            "**Conversion happens once**, here or in a mart, never twice. Currency, unit and FX live here.",
        ),
        (
            "Marts",
            "transform/models/marts/",
            ["fct_*", "dim_*", "meta.grain", "tests", "exposures"],
            "Every mart declares its grain. Sisters that conform carry identical SQL, and a group test refuses drift.",
        ),
        (
            "Semantic",
            "transform/models/semantic/",
            ["MetricFlow", "measures", "metrics", "dimensions"],
            "A business question is answered with `query_metrics`. Raw SQL that recomputes a metric is a bug.",
        ),
        (
            "Reporting",
            "reporting/",
            ["Evidence", "one page per metric"],
            "A projection of the metrics, regenerated by `pf bootstrap`, never a number the semantic layer lacks.",
        ),
        (
            "Graph",
            "kg/graph.json · kg/context_card.md",
            ["pf kg build", "pf kg card", "ADRs as nodes"],
            "Ask the graph before reading files: `kg_search`, `kg_neighbors`, `kg_path`, `impact_analysis`.",
        ),
        (
            "Orchestration",
            "src/<module>/definitions.py",
            ["Dagster", "platform factory", "one writer pool"],
            "Each project is its own code location, so sisters run in parallel and never share a writer.",
        ),
        ("Roll-up", "projects/<group>-rollup/", ["roster.py", "ATTACH READ_ONLY", "conformed marts"], ""),
    ]


def _steps(g: Guide) -> list[tuple[str, str, str]]:
    """Onboarding, in the order the outputs feed each other: (title, body, commands)."""
    domains = ", ".join(d for d, _ in g.domains) or "b2b_saas"
    return [
        (
            "Create the group if it is new",
            (
                "This writes the group manifest, the tools, loops, notify and air files, an ontology instance, a "
                "CLAUDE.md, a plugin shell for group skills, a shared dbt package and an evals README. Then pick the "
                "platform classes in `ontology/instance.yaml`. If the domain has words the platform lacks, add them in "
                "`ontology/extension.yaml`, the way commodity added `Commodity` and the `unit_price` role."
            ),
            f"uv run pf new-group <group> --domain b2b_saas   # domains: {domains}",
        ),
        (
            "Plan the project, then apply",
            (
                "The plan shows capabilities, gate rules and CI jobs, and blocks on a missing group or a taken "
                "directory. "
                "Apply writes the files and runs every bootstrap step listed below. Add `--with bigquery --without "
                "snowflake` for a different warehouse, or `--rollup --sisters a,b` for a cross-entity project."
            ),
            "uv run pf new-project <group> <project> --plan\nuv run pf new-project <group> <project>",
        ),
        (
            "Work inside the project only",
            (
                "This launches Claude scoped to that project. Its settings deny reading sisters and secrets, allow the "
                "`pf`, dbt and MetricFlow commands, and load the platform toolkits plus the group's own skills."
            ),
            "uv run pf work <group> <project>",
        ),
        (
            "Write sources and annotate them",
            (
                "One file per source under `src/<module>/sources/`. Every resource gets an `annotate` call with "
                "concept, "
                "grain, roles, renames and links before any model exists. The `quick-start` skill walks this: find the "
                "source, ingest, annotate, validate, then stop and review the annotation table."
            ),
            "",
        ),
        (
            "Seed and generate",
            (
                "Seed runs dlt, exports the contract, runs the ontology-derived monitors, builds dbt, parses the "
                "manifests and rebuilds the graph and the card. Then generate staging from the contract."
            ),
            "uv run pf seed <group> <project>\nuv run pf gen-staging <group> <project>",
        ),
        (
            "Hand-write intermediate, marts and semantic",
            (
                "Declare grain on every mart. Put conversion in one intermediate model. Define at least one metric. "
                "Add dbt tests under `transform/tests/`."
            ),
            "",
        ),
        (
            "Rebuild the graph and check",
            (
                "Read `kg/context_card.md` and its Known gaps line. The exit criteria are a clean exit, no line "
                "starting with ✗, and zero conformance errors."
            ),
            (
                "uv run pf kg build <group> <project> && uv run pf kg card <group> <project>\n"
                "uv run pf check\nuv run pf bootstrap <group> <project>"
            ),
        ),
        (
            "Record what the graph cannot hold",
            (
                "Business rules go in the project `CLAUDE.md`, under its token budget. Decisions go in "
                "`decisions/ADR-*.md`, where `pf kg build` turns them into graph nodes. Lessons for the next agent go "
                "through `pf memory add`."
            ),
            "",
        ),
        (
            "Decide the family-level settings once",
            (
                "Enable tools with `pf tool enable`. Fill `air.yaml` from the controls that already pass. Set loop "
                "cadence and waivers in `loops.yaml`. Point `notify.yaml` at environment-variable names, never URLs."
            ),
            "uv run pf tool enable recce <group>\nuv run pf air baseline <group> --suggest",
        ),
        (
            "If a roll-up exists, register the sister",
            (
                "Add it to the roll-up's roster and to the group manifest's resources, then re-seed the roll-up. The "
                "commodity group's `add-a-market` skill is the template for this."
            ),
            "uv run pf seed <group> <group>-rollup",
        ),
        (
            "Ship through the gates",
            (
                "Install the hook on a fresh clone. Open a pull request and the generated workflow runs. `pf pr "
                "report` "
                "writes one verdict of block, review or clear."
            ),
            "uv run pf install-hook\nuv run pf pr report",
        ),
    ]


def document(g: Guide) -> list[tuple[str, str, str, list[Block]]]:
    """The guide as sections: (id, eyebrow, title, blocks)."""
    f = g.facts
    tiers: Block = (
        "table",
        ["Layer", "Path", "Touch it when onboarding?"],
        [
            ["Platform", "`platform/`", "Never. Shared by every project."],
            ["Vendored upstreams", "`vendor/`", "Never. Pinned submodules; bumping one is a human decision."],
            ["Group", "`groups/<group>/`", "Once per family."],
            ["Project", "`groups/<group>/projects/<project>/`", "This is the work."],
        ],
    )
    group_rows = [
        [f"`{gr.name}`", gr.display_name, gr.domain or "—", gr.lifecycle or "—", str(len(gr.projects))]
        for gr in g.groups
    ]
    project_rows = [
        [f"`{gr.name}/{p.name}`", str(p.tables), str(p.models), str(p.metrics), str(p.exposures), p.reading]
        for gr in g.groups
        for p in gr.projects
    ]
    loops_rows = [[f"`{n}`", a, c, d] for n, a, c, d in g.loops]
    steps_rows = [[f"`{n}`", w] for n, w in g.steps]
    caps_rows = [[f"`{n}`", "on by default" if d else "opt-in", c] for n, d, c in f.capabilities]
    stage_rows = [[f"`{n}`", t, s] for n, t, s in g.stages]
    cmd_rows = [[f"`pf {n}`", h] for n, h in g.commands]
    grp_rows = [[f"`pf {n}`", h] for n, h in g.command_groups]
    ci = ", ".join(f"`{j}`" for j in g.ci_jobs) or "the jobs its capabilities declare"

    return [
        (
            "model",
            "The idea in one minute",
            "An apartment building for companies' data",
            [
                (
                    "p",
                    (
                        "The plumbing is shared and tenants never touch it. Each family of related companies gets a "
                        "floor with a shared vocabulary. Each company gets its own apartment with its own data, "
                        "pipelines and reports. Nothing crosses between apartments except through one designated "
                        "roll-up room."
                    ),
                ),
                (
                    "p",
                    (
                        "**The hard rule:** never read another group or another sister project. Business logic does "
                        "not transfer between entities, and `gate.yaml` denies the write in both directions."
                    ),
                ),
                tiers,
                (
                    "ul",
                    [
                        (
                            "**Platform** holds the engines: the `pf` command line, the runtime factories for dlt, "
                            "dbt and "
                            "Dagster, the platform ontology, the knowledge-graph code, the MCP server an agent "
                            "calls, and "
                            f"{len(f.toolkits)} skill toolkits. Everything starts at `platform/src/pf/cli.py`."
                        ),
                        (
                            "**Group** is a family of sister companies that mean the same thing by the same words. "
                            "It holds "
                            "the ontology instance and extension, a shared dbt package of seeds and macros, optional "
                            "shared "
                            "Python connectors, and the family's decisions on tools, loops, AI controls and "
                            "notifications."
                        ),
                        (
                            "**Project** is one legal entity. It owns one DuckDB warehouse file, its dlt sources, "
                            "its dbt "
                            "models, its metrics, its dashboards and a generated knowledge graph."
                        ),
                    ],
                ),
            ],
        ),
        (
            "estate",
            "Who lives here today",
            "Groups and projects",
            [
                (
                    "p",
                    (
                        "Read from `group.yaml` and each project's tracked `kg/graph.json`, so this is true in a fresh "
                        "clone without a warehouse. A zero is a finding, not a gap in the count."
                    ),
                ),
                ("table", ["Group", "Display name", "Domain", "Lifecycle", "Projects"], group_rows),
                ("table", ["Project", "Tables", "Models", "Metrics", "Exposures", "Reading"], project_rows),
            ],
        ),
        (
            "flow",
            "End to end",
            "One company's data, source to dashboard",
            [
                (
                    "p",
                    (
                        "Every stage has an owner and one thing it may never do. The rule on each hop is where the "
                        "platform keeps its knowledge; the stage names are the conventions every project follows."
                    ),
                ),
                ("flow", _flow()),
                (
                    "p",
                    (
                        "`pf seed <group> <project>` runs the first nine stages in one command: dlt, contract, "
                        "monitors, dbt build, dbt parse, graph, card."
                    ),
                ),
            ],
        ),
        (
            "guardrails",
            "Guardrails",
            "What fires whether or not anyone remembers",
            [
                (
                    "ul",
                    [
                        (
                            "`pf check` validates every source against the ontology and reports the blast radius of "
                            "working-tree changes."
                        ),
                        (
                            "`pf impact <group> <project> model:<name>` walks the graph downstream and names every "
                            "model, "
                            "metric, dimension and exposure affected, with owners. It fails on a breaking change and "
                            "is the "
                            "merge gate."
                        ),
                        (
                            "A pre-commit hook and a Claude PreToolUse hook enforce `gate.yaml`: secrets, generated "
                            "files "
                            "and `provenance/` are denied, and model edits print their blast radius."
                        ),
                        (
                            f"One generated CI workflow per project runs {ci}, each guarded so a change to a page "
                            "never "
                            "starts a dbt review."
                        ),
                        (
                            "Every agent action is written to `provenance/` in five stages with a hash chain and a "
                            "timestamp anchor. Agents cannot edit that record."
                        ),
                        "`pf tokens` fails the build if an always-loaded context file goes over its budget.",
                    ],
                ),
                ("h3", "Loops: scheduled, budgeted agent work"),
                (
                    "p",
                    (
                        "L1 reports and never writes; L2 may patch inside what `gate.yaml` allows. A group tunes "
                        "cadence and waivers in `loops.yaml` and may only lower a level, never raise one."
                    ),
                ),
                ("table", ["Loop", "Level", "Cadence", "What it does"], loops_rows),
            ],
        ),
        (
            "steps",
            "Step by step",
            "Onboarding a new company",
            [
                (
                    "p",
                    (
                        "Decide first whether the company joins an existing family or starts one. Join only if a "
                        "roll-up across it and its sisters would add meaningful numbers. If the vocabulary differs, it "
                        "is a new group, and that costs one `pf new-group`. `docs/SCAFFOLDING.md` is the full "
                        "reference."
                    ),
                ),
                ("steps", _steps(g)),
                ("h3", "What apply and bootstrap run"),
                (
                    "p",
                    (
                        "Everything after the files lives in one ordered, idempotent list, shared by `pf new-project` "
                        "and `pf bootstrap`. A step that reports ✗ is re-run with `pf bootstrap`, never hand-fixed."
                    ),
                ),
                ("table", ["Step", "Why it exists"], steps_rows),
                ("h3", "Capabilities a project can be scaffolded with"),
                (
                    "p",
                    (
                        "`--plan` shows what the ones you pick will do. `pf bootstrap --all` carries a new default "
                        "into "
                        "projects that already exist."
                    ),
                ),
                ("table", ["Capability", "Default", "Contributes"], caps_rows),
            ],
        ),
        (
            "adopt",
            "Already have a dbt repo?",
            "Adopting an existing repository",
            [
                (
                    "p",
                    (
                        "`pf onboard` moves models into the layer convention, merges dependency files and replaces the "
                        "orchestrator. It cannot infer annotations, grains or foreign keys, so it ends with a "
                        "checklist "
                        "and `pf check` keeps failing until that work is done."
                    ),
                ),
                (
                    "code",
                    (
                        "uv run pf onboard <group> <project> <git-url-or-path>          # plan only\n"
                        "uv run pf onboard <group> <project> <git-url-or-path> --apply\n"
                        "uv run pf align status <group> <project>"
                    ),
                    "bash",
                ),
                (
                    "p",
                    (
                        "The align ladder then walks the stages below in order. Each has a code-based evaluate and "
                        "validate phase, so an agent cannot talk its way past a gate, and the implement phase is the "
                        "only one left to judgement."
                    ),
                ),
                ("table", ["Stage", "Title", "Done when"], stage_rows),
                (
                    "p",
                    (
                        "Leaving is `pf offboard <group>`: it enumerates everything the family owns from its manifest "
                        "and removes only with `--apply`."
                    ),
                ),
            ],
        ),
        (
            "commands",
            "The tool",
            "Every pf command",
            [
                (
                    "p",
                    (
                        f"{len(g.commands)} commands and {len(g.command_groups)} command groups, read from the CLI "
                        "itself. `uv run pf <command> --help` is always current."
                    ),
                ),
                ("table", ["Command", "What it does"], cmd_rows),
                ("table", ["Group", "What it covers"], grp_rows),
            ],
        ),
        (
            "more",
            "Read more",
            "Where the detail lives",
            [
                ("docs", g.docs),
                (
                    "p",
                    "Toolkits are skills every project loads and none copies: "
                    + ", ".join(f"`{t}`" for t in f.toolkits)
                    + ". `platform/toolkits/ROUTING.md` says which wins when they overlap.",
                ),
            ],
        ),
        (
            "true",
            "Keeping this true",
            "Generated, checked, never hand-edited",
            [
                (
                    "code",
                    (
                        "uv run pf guide build      # regenerate docs/ONBOARDING.md and docs/onboarding.html\n"
                        "uv run pf guide check      # fail if they and the repository disagree"
                    ),
                    "bash",
                ),
                (
                    "p",
                    (
                        "`pf context refresh` regenerates this page with the other generated context, and the "
                        "`agent-context` workflow checks it on every pull request. A pull request that renames a "
                        "command or adds a project cannot merge while this page still describes the old repository."
                    ),
                ),
            ],
        ),
    ]


# --------------------------------------------------------------- markdown ---
def _md_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _md_table(header: list[str], rows: list[list[str]]) -> list[str]:
    return [
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---"] * len(header)) + "|",
        *["| " + " | ".join(_md_cell(c) for c in r) + " |" for r in rows],
        "",
    ]


def _md_block(b: Block) -> list[str]:
    kind = b[0]
    if kind == "p":
        return [b[1], ""]
    if kind == "h3":
        return [f"### {b[1]}", ""]
    if kind == "ul":
        return [*[f"- {x}" for x in b[1]], ""]
    if kind == "code":
        return [f"```{b[2]}", b[1], "```", ""]
    if kind == "table":
        return _md_table(b[1], b[2])
    if kind == "docs":
        return _md_table(["Document", "What it covers"], [[f"[{f}]({f})", t] for f, t in b[1]])
    if kind == "steps":
        out = []
        for i, (title, body, code) in enumerate(b[1], 1):
            out.append(f"{i}. **{title}.** {body}")
            if code:
                out += ["", "   ```bash", *[f"   {ln}" for ln in code.splitlines()], "   ```"]
            out.append("")
        return out
    if kind == "flow":
        out = []
        for name, where, chips, rule in b[1]:
            out.append(f"- **{name}** · `{where}` · " + " · ".join(chips))
            if rule:
                out.append(f"  - ↓ {rule}")
        return [*out, ""]
    raise ValueError(f"unknown block kind {kind!r}")


def render_markdown(g: Guide) -> str:
    """The document. Deterministic: it is compared byte for byte."""
    f = g.facts
    out = [
        f"# {TITLE}",
        "",
        "GENERATED by `pf guide build`. Do not hand-edit — `pf guide check` fails",
        "when this file and the repository disagree, and the repository wins.",
        "",
        (
            f"{len(f.groups)} groups · {f.projects} projects · {len(f.toolkits)} toolkits · "
            f"{f.upstreams} pinned upstreams · {len(g.commands)} commands"
        ),
        "",
        "Shared infrastructure, business logic per company. This is the whole",
        "repository as a newcomer needs it, from the three tiers to the command",
        "sequence that brings a new company in. The HTML twin, `onboarding.html`,",
        "is the same page for publishing.",
        "",
    ]
    for _id, eyebrow, title, blocks in document(g):
        out += ["---", "", f"## {title}", "", f"*{eyebrow}*", ""]
        for b in blocks:
            out += _md_block(b)
    return "\n".join(out).rstrip("\n") + "\n"


# ------------------------------------------------------------------- html ---
_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _inline(text: str) -> str:
    """Escape, then the three inline marks the document uses. Links become plain
    code: the page is published away from the repository, where a relative
    link would point at nothing."""
    parts = _CODE.split(html.escape(text, quote=True))
    out = []
    for i, part in enumerate(parts):
        if i % 2:
            out.append(f"<code>{part}</code>")
        else:
            part = _LINK.sub(r"<code>\1</code>", part)
            out.append(_BOLD.sub(r"<strong>\1</strong>", part))
    return "".join(out)


def _html_table(header: list[str], rows: list[list[str]]) -> list[str]:
    out = [
        '<div class="scroll"><table>',
        "<thead><tr>",
        *[f"<th>{_inline(h)}</th>" for h in header],
        "</tr></thead>",
        "<tbody>",
    ]
    for r in rows:
        out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>")
    out += ["</tbody></table></div>"]
    return out


def _html_block(b: Block) -> list[str]:
    kind = b[0]
    if kind == "p":
        return [f'<p class="prose">{_inline(b[1])}</p>']
    if kind == "h3":
        return [f"<h3>{_inline(b[1])}</h3>"]
    if kind == "ul":
        return ['<ul class="prose">', *[f"<li>{_inline(x)}</li>" for x in b[1]], "</ul>"]
    if kind == "code":
        return [f"<pre><code>{html.escape(b[1])}</code></pre>"]
    if kind == "table":
        return _html_table(b[1], b[2])
    if kind == "docs":
        return _html_table(["Document", "What it covers"], [[f"`docs/{f}`", t] for f, t in b[1]])
    if kind == "steps":
        out = ['<ol class="steps">']
        for title, body, code in b[1]:
            # One grid cell for the whole body, so the number column never takes the prose.
            out.append(f'<li><div class="step-body"><h3>{_inline(title)}</h3><p>{_inline(body)}</p>')
            if code:
                out.append(f"<pre><code>{html.escape(code)}</code></pre>")
            out.append("</div></li>")
        return [*out, "</ol>"]
    if kind == "flow":
        out = ['<figure class="figure"><div class="scroll"><div class="flow">']
        for name, where, chips, rule in b[1]:
            cls = "shr" if name in ("Roll-up",) else "own"
            out.append(
                f'<div class="stage {cls}"><div class="stage-name">{html.escape(name)}'
                f"<span>{html.escape(where)}</span></div>"
                '<div class="chips">'
                + "".join(f'<span class="chip">{html.escape(c)}</span>' for c in chips)
                + "</div></div>"
            )
            if rule:
                out.append(f'<div class="hop"><div class="arrow">↓</div><div>{_inline(rule)}</div></div>')
        out.append(
            "</div></div><figcaption>Owned by the company in teal; the roll-up, shared by the family, "
            "in indigo. Each hop names the rule that governs it.</figcaption></figure>"
        )
        return out
    raise ValueError(f"unknown block kind {kind!r}")


_CSS = """
:root {
  --paper: #f3f6f7; --surface: #ffffff; --surface-2: #e8edef;
  --ink: #15202a; --ink-2: #46565f; --ink-3: #7b8a93;
  --line: #d2d9dd; --line-strong: #b3bfc5;
  --owned: #0f6a6a; --shared: #414c8c; --bound: #8a5800; --ok: #2d6b4d;
  --display: "Instrument Serif", Georgia, "Times New Roman", serif;
  --body: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --paper: #0e1418; --surface: #151e24; --surface-2: #1c272e;
    --ink: #e5ecf0; --ink-2: #a1b1ba; --ink-3: #6d7e87;
    --line: #293640; --line-strong: #3b4c57;
    --owned: #5ec5bd; --shared: #9ba7e9; --bound: #d9a642; --ok: #6dbf90;
  }
}
:root[data-theme="dark"] {
  --paper: #0e1418; --surface: #151e24; --surface-2: #1c272e;
  --ink: #e5ecf0; --ink-2: #a1b1ba; --ink-3: #6d7e87;
  --line: #293640; --line-strong: #3b4c57;
  --owned: #5ec5bd; --shared: #9ba7e9; --bound: #d9a642; --ok: #6dbf90;
}
body { margin: 0; background: var(--paper); color: var(--ink); font-family: var(--body);
  font-size: 16px; line-height: 1.62; -webkit-font-smoothing: antialiased; }
.wrap { max-width: 1060px; margin: 0 auto; padding-inline: 20px; padding-block: 0 72px; }
.prose { max-width: 66ch; }
h1, h2 { font-family: var(--display); font-weight: 400; text-wrap: balance; letter-spacing: -0.01em; }
h1 { font-size: clamp(2.4rem, 6vw, 3.6rem); line-height: 1.04; margin: 0 0 12px; }
h2 { font-size: clamp(1.6rem, 3.6vw, 2.1rem); line-height: 1.12; margin: 0 0 4px; }
h3 { font-size: 1.12rem; line-height: 1.3; margin: 26px 0 6px; font-weight: 600; text-wrap: balance; }
p { margin: 0 0 14px; }
ul.prose { padding-left: 1.2em; margin: 0 0 14px; }
ul.prose li { margin-bottom: 8px; }
a { color: var(--owned); text-underline-offset: 2px; }
a:focus-visible { outline: 2px solid var(--owned); outline-offset: 2px; }
code, pre { font-family: var(--mono); font-variant-ligatures: none; }
code { font-size: 0.855em; }
p code, li code, td code, h3 code { background: var(--surface-2); padding: 0.08em 0.34em; border-radius: 3px; }
pre { background: var(--surface-2); border: 1px solid var(--line); border-radius: 2px; padding: 12px 14px;
  overflow-x: auto; font-size: 0.83rem; line-height: 1.55; margin: 0 0 16px; }
pre code { background: none; padding: 0; font-size: inherit; }
.eyebrow { font-family: var(--mono); font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.14em;
  color: var(--ink-3); margin: 0 0 10px; }
header.top { border-bottom: 1px solid var(--line); padding-block: 56px 28px; margin-bottom: 28px; }
.standfirst { font-size: 1.12rem; color: var(--ink-2); max-width: 60ch; margin: 0 0 18px; }
.snapshot { font-family: var(--mono); font-size: 0.78rem; color: var(--ink-3); margin: 0; }
nav.toc { display: flex; flex-wrap: wrap; gap: 6px 14px; font-family: var(--mono); font-size: 0.78rem;
  margin-bottom: 8px; }
nav.toc a { color: var(--ink-2); text-decoration: none; border-bottom: 1px solid var(--line); }
nav.toc a:hover { color: var(--owned); border-bottom-color: var(--owned); }
section { padding-block: 34px 0; }
section + section { border-top: 1px solid var(--line); margin-top: 34px; }
.sect-head { margin-bottom: 18px; }
.facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1px;
  background: var(--line); border: 1px solid var(--line); border-radius: 2px; margin: 0; }
.fact { background: var(--surface); padding: 12px 14px; }
.fact dt { font-family: var(--mono); font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.09em;
  color: var(--ink-3); }
.fact dd { margin: 4px 0 0; font-size: 1.15rem; font-variant-numeric: tabular-nums; }
.scroll { overflow-x: auto; padding-bottom: 4px; margin: 0 0 18px; }
table { border-collapse: collapse; width: 100%; font-size: 0.9rem; min-width: 460px; }
th { text-align: left; font-family: var(--mono); font-size: 0.68rem; text-transform: uppercase;
  letter-spacing: 0.09em; color: var(--ink-3); font-weight: 500; padding: 8px 10px 8px 0;
  border-bottom: 1px solid var(--line-strong); }
td { padding: 8px 10px 8px 0; border-bottom: 1px solid var(--line); vertical-align: top; }
td:first-child { white-space: nowrap; }
.figure { margin: 0 0 8px; }
figcaption { font-size: 0.83rem; color: var(--ink-3); margin-top: 10px; font-family: var(--mono); }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { font-family: var(--mono); font-size: 0.78rem; background: var(--surface); border: 1px solid var(--line);
  border-radius: 2px; padding: 3px 8px; white-space: nowrap; }
.flow { display: grid; gap: 0; min-width: 460px; }
.stage { display: grid; grid-template-columns: 172px 1fr; gap: 16px; border: 1px solid var(--line);
  border-left: 3px solid var(--line-strong); background: var(--surface); padding: 12px 14px; border-radius: 2px; }
.stage.own { border-left-color: var(--owned); }
.stage.shr { border-left-color: var(--shared); }
.stage-name { font-weight: 600; font-size: 0.95rem; }
.stage-name span { display: block; font-family: var(--mono); font-size: 0.7rem; font-weight: 400;
  color: var(--ink-3); margin-top: 2px; overflow-wrap: anywhere; }
.hop { display: grid; grid-template-columns: 172px 1fr; gap: 16px; padding: 7px 14px; font-size: 0.86rem;
  color: var(--ink-2); }
.hop .arrow { font-family: var(--mono); color: var(--ink-3); text-align: center; }
.hop strong { color: var(--bound); font-weight: 600; }
ol.steps { list-style: none; counter-reset: step; padding: 0; margin: 0 0 8px; max-width: 72ch; }
ol.steps li { counter-increment: step; display: grid; grid-template-columns: 44px minmax(0, 1fr); gap: 12px;
  padding: 14px 0; border-top: 1px solid var(--line); }
ol.steps li::before { content: counter(step, decimal-leading-zero); font-family: var(--mono);
  color: var(--owned); font-size: 0.95rem; padding-top: 4px; }
ol.steps h3 { margin: 0 0 6px; }
ol.steps p { margin: 0 0 10px; }
ol.steps pre { margin: 0; }
.step-body { min-width: 0; }
footer { border-top: 1px solid var(--line); margin-top: 48px; padding-top: 18px; font-size: 0.86rem;
  color: var(--ink-3); }
@media (max-width: 560px) {
  .stage, .hop, ol.steps li { grid-template-columns: 1fr; gap: 6px; }
  .hop .arrow { text-align: left; }
}
@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto !important; } }
"""


def render_html(g: Guide) -> str:
    """The same page as a standalone document, for publishing."""
    f = g.facts
    secs = document(g)
    out = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
        f"<title>{html.escape(TITLE)}</title>",
        (
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Serif'
            '&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">'
        ),
        "<style>" + _CSS + "</style>",
        "</head>",
        "<body>",
        '<div class="wrap">',
        '<header class="top">',
        '<p class="eyebrow">data-platform · onboarding</p>',
        f"<h1>{html.escape(TITLE)}</h1>",
        "<!-- snapshot -->",
        (
            '<p class="standfirst">Shared infrastructure, business logic per company. This is the whole repository '
            "as a newcomer needs it, from the three tiers to the command sequence that brings a new company in. "
            "Generated from the repository and checked on every pull request.</p>"
        ),
        '<nav class="toc">' + "".join(f'<a href="#{i}">{html.escape(t)}</a>' for i, _e, t, _b in secs) + "</nav>",
        "</header>",
        '<dl class="facts">',
        f'<div class="fact"><dt>Groups</dt><dd>{len(f.groups)}</dd></div>',
        f'<div class="fact"><dt>Projects</dt><dd>{f.projects}</dd></div>',
        f'<div class="fact"><dt>Toolkits</dt><dd>{len(f.toolkits)}</dd></div>',
        f'<div class="fact"><dt>Pinned upstreams</dt><dd>{f.upstreams}</dd></div>',
        f'<div class="fact"><dt>pf commands</dt><dd>{len(g.commands)}</dd></div>',
        f'<div class="fact"><dt>Tests</dt><dd>{f.tests.get("tests", 0)}</dd></div>',
        "</dl>",
    ]
    for sid, eyebrow, title, blocks in secs:
        out += [
            f'<section id="{sid}">',
            '<div class="sect-head">',
            f'<p class="eyebrow">{html.escape(eyebrow)}</p>',
            f"<h2>{html.escape(title)}</h2>",
            "</div>",
        ]
        for b in blocks:
            out += _html_block(b)
        out.append("</section>")
    out += [
        (
            "<footer>Generated by <code>pf guide build</code> from the repository. <code>pf guide check</code> fails "
            "the build when this page and the repository disagree; the <code>agent-context</code> workflow runs it on "
            "every pull request.</footer>"
        ),
        "</div>",
        "</body>",
        "</html>",
        "",
    ]
    return "\n".join(out)


# ------------------------------------------------------------------ files ---
def md_path(root: str | Path) -> Path:
    return Path(root) / "docs" / "ONBOARDING.md"


def html_path(root: str | Path) -> Path:
    return Path(root) / "docs" / "onboarding.html"


def build(root: str | Path) -> tuple[Guide, list[Path]]:
    """Write both renderings; return the guide and the files that changed."""
    g = gather(root)
    changed = []
    for path, content in ((md_path(root), render_markdown(g)), (html_path(root), render_html(g))):
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            changed.append(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return g, changed


def drift(root: str | Path) -> str:
    """Empty when both committed renderings match the repository."""
    g = None
    for path, render in ((md_path(root), render_markdown), (html_path(root), render_html)):
        if not path.exists():
            return f"{path} does not exist; run `pf guide build`"
        g = g or gather(root)
        if path.read_text(encoding="utf-8") != render(g):
            return f"{path} is stale; run `pf guide build`"
    return ""
