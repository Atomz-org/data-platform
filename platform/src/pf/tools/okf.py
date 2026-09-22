"""OKF — the semantic layer as portable, validated context, as a Tool.

Open Knowledge Format (OKF v0.1, Google's knowledge-catalog spec) is what an
AI agent, an analyst or a catalogue reads to learn what a table and a column
*mean*. `vendor/okf-weaver` produces such a bundle from a bare dbt manifest by
asking Claude; this platform produces one from what it already declares —
`pf.projections.okf` — and takes from the weaver its validation gate, its
layout and, on request, its generator. This module is the wiring: one
declaration that gives every project an `okf/` bundle, a gate rule over it, a
Dagster asset downstream of the models it describes, a doctor, and the verbs.

Two bundles, connected. `platform/okf/` is the platform ontology as OKF, and
every project's `okf/index.md` links to it; the project's concept files link
to the platform's concept files. `pf tool okf build --platform` writes the
platform's; every `pf bootstrap` writes a project's and refreshes the
platform's, so the two cannot disagree for longer than one bootstrap.

## What `weave` is, and is not

`pf tool okf weave <group> <project>` runs the weaver's generator — Claude,
per table, tool-constrained, one repair pass — over the models the MDL
projects, and writes `okf/weave.md`: the weaver's proposed definitions, each
with the weaver's own confidence, beside what the platform holds. It never
writes into the bundle. A proposal becomes true by being promoted into
`contracts/annotations.yaml` or a model `description` and rebuilt, in a pull
request, which is where a definition is reviewed here. The run needs
`ANTHROPIC_API_KEY` in the environment, is recorded in the provenance ledger
as an agent action, and reports its token usage.

## What the surface is

`pf tool okf serve` starts the weaver's own API (FastAPI) through `uvx`,
built from the submodule into uv's cache rather than into `vendor/`, which
stays read-only. `pf ui` → Review can embed its docs page. It is there for
someone who wants the weaver's interface over a manifest; nothing in the
platform depends on it running.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from pf.capabilities import Capability
from pf.tools.spec import DbtBinding, Surface, Tool, ToolContext, ToolContribution

DOCS = """\
# OKF — {{group}}/{{project}}

`okf/` is this project's semantic layer as an **Open Knowledge Format** bundle:
one Markdown file with YAML frontmatter per table, per concept and per metric,
and an `index.md` that declares the version and links every one. It is what an
agent, an analyst or a catalogue reads to learn what a table and a column mean
— generated from the MDL, the ontology annotations and the metric definitions
by `pf tool okf build`, validated through the vendored OKF models before a file
is written, and never hand-edited.

```bash
pf tool okf build {{group}} {{project}}     # regenerate from the semantic layer
pf tool okf check {{group}} {{project}}     # stale or non-conformant? exits 1
pf tool okf weave {{group}} {{project}}     # ask the weaver for what the platform lacks
pf tool okf serve                          # the weaver's own API, locally
```

## Where a definition comes from

| In the bundle | Read from |
|---|---|
| a table's description, layer, grain | the model's properties in `mdl/mdl.json` |
| a column's definition | the ontology role on it (`contracts/annotations.yaml`) |
| the concept a table instantiates | the relation the MDL join names, else the class whose identity is the key |
| a metric | `transform/models/semantic/` |

Confidence is a fact, not a guess: `1.00` where the platform holds a
declaration, `0.00` where it holds none. A `0.00` is a column to annotate.

## Connected to the platform

`okf/index.md` names `platform/okf/index.md` — the platform ontology in the
same format — and a concept file links to the platform's when the class is the
platform's, or says `okf_x_defined_in: group` when this family's extension
declared it. Follow the link to the definition every sister shares.

## Weave

`weave` runs OKF Weaver's generator over the tables here and writes
`okf/weave.md`: proposed definitions with the weaver's confidence, next to
what the platform holds. Nothing lands in the bundle from it. Promote a
proposal into an annotation or a model description, rebuild, and it becomes
true. Needs `ANTHROPIC_API_KEY`; recorded in the provenance ledger.
"""

CAPABILITY = Capability(
    name="okf",
    description="Open Knowledge Format bundle: the semantic layer as portable, validated context for agents.",
    files={"docs/okf.md": DOCS},
    settings={"permissions": {"allow": ["Bash(pf tool okf:*)"]}},
    gate={
        # Generated from the semantic layer and validated on the way out. A
        # hand edit forks the bundle from the annotations it claims to project,
        # and the next build discards it without a word.
        "denylist": [
            "**/okf/index.md",
            "**/okf/log.md",
            "**/okf/tables/**",
            "**/okf/concepts/**",
            "**/okf/metrics/**",
            "**/okf/roles/**",
        ],
    },
    default_enabled=True,
)

DEFAULT_PORT = 8010
BACKEND = Path("vendor") / "okf-weaver" / "backend"


# ---------------------------------------------------------------- helpers --
def okf_dir(project_dir: Path) -> Path:
    return project_dir / "okf"


def has_mdl(project_dir: Path) -> bool:
    return (project_dir / "mdl" / "mdl.json").is_file()


def _root(project_dir: Path) -> Path:
    return project_dir.parents[3]


def health() -> dict[str, Any]:
    """Is the upstream checked out, and can `weave` reach a model?"""
    from pf.cli import root as repo_root
    from pf.projections.okf import NotVendored, vendored

    try:
        models = vendored(repo_root())
    except NotVendored as exc:
        return {"ok": False, "detail": str(exc)}
    detail = f"okf-weaver at OKF {models.OKF_SPEC_VERSION}"
    if not os.environ.get("ANTHROPIC_API_KEY"):
        detail += " · weave needs ANTHROPIC_API_KEY"
    if not shutil.which("uvx"):
        detail += " · serve needs uvx"
    return {"ok": True, "detail": detail}


# -------------------------------------------------------------- bootstrap --
def bootstrap_project(root: Path, group: str, project: str, project_dir: Path, config: dict[str, Any]) -> Any:
    """The project's bundle, and the platform's beside it. Skipped where there is no MDL yet."""
    from pf.scaffold.bootstrap import StepResult

    if not has_mdl(project_dir):
        return StepResult("okf", "skipped", "no mdl/mdl.json yet (`pf semantic mdl`)")
    from pf.projections.okf import NotVendored, write_platform, write_project

    try:
        r = write_project(root, group, project)
        write_platform(root)
    except NotVendored as exc:
        return StepResult("okf", "skipped", str(exc))
    return StepResult("okf", "ok", f"{r['tables']} table(s), {r['concepts']} concept(s), {r['metrics']} metric(s)")


# ---------------------------------------------------------------- dagster --
def dagster_assets(ctx: ToolContext) -> ToolContribution:
    """The bundle as an asset downstream of every model it describes."""
    from dagster import AssetKey, MetadataValue, asset

    project_dir = Path(ctx.project_dir)
    if not has_mdl(project_dir):
        return ToolContribution()
    from pf.projections.okf import gather

    prefix = ctx.project.replace("-", "_")
    facts = gather(_root(project_dir), ctx.group, ctx.project)
    deps = [AssetKey([prefix, str(m["name"])]) for m in facts.models]

    @asset(
        name="okf",
        key_prefix=[prefix],
        group_name="semantics",
        deps=deps,
        description="OKF bundle projected from the semantic layer; validated on build.",
        compute_kind="okf",
        metadata={"dagster/kind": "okf", "tool": "okf"},
    )
    def _okf(context) -> None:  # noqa: ANN001 — see dagster_runtime note
        from pf.projections.okf import conformance, write_project

        r = write_project(_root(project_dir), ctx.group, ctx.project)
        problems = conformance(r["path"])
        context.add_output_metadata(
            {
                "tables": r["tables"],
                "concepts": r["concepts"],
                "metrics": r["metrics"],
                "conformance_problems": len(problems),
                "path": MetadataValue.path(str(r["path"])),
            }
        )

    return ToolContribution(assets=[_okf])


# ------------------------------------------------------------------ weave --
def weave(root: Path, group: str, project: str, *, context: str | None = None, model_id: str = "") -> dict[str, Any]:
    """Run the weaver over this project's models; write `okf/weave.md` as proposals.

    Bounded to the tables the MDL projects, so a run costs what the semantic
    layer is worth and not what the raw layer is. The platform's declarations
    are shown beside every proposal; none is overwritten.
    """
    from pf.projections.okf import gather, vendored

    models = vendored(root)
    import okf_weaver.ai.generate as gen
    from okf_weaver.ingest.dbt_manifest import parse_dbt_manifest

    pdir = root / "groups" / group / "projects" / project
    manifest_path = pdir / "transform" / "target" / "manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"{manifest_path} is missing — run `dbt parse` in {pdir / 'transform'} first")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("weave needs ANTHROPIC_API_KEY in the environment; nothing was sent")
    facts = gather(root, group, project)
    keep = {str(m["name"]) for m in facts.models}
    schema = parse_dbt_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))
    tables = [t for t in schema.tables if t.name in keep]
    if not tables:
        raise RuntimeError("no MDL model has a manifest node — `pf semantic mdl` and `dbt parse` disagree")
    schema = models.SchemaIR(source_format=schema.source_format, tables=tables)
    declared = _declared(facts)

    usage: dict[str, int] = {}
    got: dict[str, Any] = {}
    model_id = model_id or gen.DEFAULT_MODEL

    def run() -> None:
        client = gen.make_client()
        for kind, name, payload in gen.generate_bundle(
            schema, client=client, model_id=model_id, context=context, usage=usage
        ):
            if kind == "table":
                got[name] = payload

    try:
        from pf.provenance import action
    except Exception:  # noqa: BLE001 — recording is best-effort; the run is not
        action = None
    if action is not None:
        with action(
            root,
            tool="okf-weaver",
            target=f"groups/{group}/projects/{project}/okf/weave.md",
            summary=f"weave {len(tables)} table(s) through {model_id}",
            group=group,
            project=project,
        ) as box:
            run()
            box["detail"] = f"{len(got)} table(s); usage {json.dumps(usage, sort_keys=True)}"
    else:
        run()

    out = okf_dir(pdir) / "weave.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_weave_md(group, project, model_id, got, declared, usage, gen), encoding="utf-8")
    return {"path": out, "tables": len(got), "usage": usage}


def _declared(facts: Any) -> dict[str, dict[str, str]]:
    """table -> {column -> what the platform holds}, with '' where it holds nothing."""
    roles = facts.onto.roles if facts.onto is not None else {}
    out: dict[str, dict[str, str]] = {}
    for m in facts.models:
        held = {"": str((m.get("properties") or {}).get("description") or "")}
        for c in m.get("columns") or []:
            role = str((c.get("properties") or {}).get("pf.role") or "")
            r = roles.get(role)
            held[str(c["name"])] = f"{role}: {r.description}" if r is not None else ""
        out[str(m["name"])] = held
    return out


def _weave_md(
    group: str,
    project: str,
    model_id: str,
    got: dict[str, Any],
    declared: dict[str, dict[str, str]],
    usage: dict[str, int],
    gen: Any,
) -> str:
    import yaml

    front = {
        "type": "Proposal",
        "title": f"weave — {group}/{project}",
        "okf_x_model": model_id,
        "okf_x_tables": len(got),
        "okf_x_usage": {k: int(v) for k, v in sorted(usage.items())},
    }
    try:
        cost = gen.usage_summary(usage, model_id)
    except Exception:  # noqa: BLE001
        cost = None
    if isinstance(cost, dict):
        front["okf_x_usage_summary"] = {k: v for k, v in cost.items() if isinstance(v, (int, float, str))}
    lines = [
        f"# Proposals from OKF Weaver — {group}/{project}",
        "",
        "Not part of the bundle. Each row is what the weaver's model proposed and how sure",
        "it was, beside what the platform declares. Promote a proposal by writing it into",
        "`contracts/annotations.yaml` (a role) or the model's `description`, then rebuild;",
        "a column the platform already declares keeps its declaration.",
        "",
    ]
    for name in sorted(got):
        t = got[name]
        held = declared.get(name, {})
        lines += [
            f"## {name}",
            "",
            f"**Proposed:** {' '.join(t.description.split())} _(confidence {t.confidence:.2f})_",
            "",
            "**Platform holds:** " + (held.get("", "") or "_no description_"),
            "",
            "| Column | Proposed definition | Confidence | Platform holds |",
            "|---|---|---|---|",
        ]
        for c in t.columns:
            proposed = " ".join(c.definition.split()).replace("|", "\\|")
            lines.append(f"| `{c.name}` | {proposed} | {c.confidence:.2f} | {held.get(c.name, '') or '—'} |")
        lines.append("")
    return "---\n" + yaml.safe_dump(front, sort_keys=False).strip() + "\n---\n\n" + "\n".join(lines)


# ------------------------------------------------------------------ serve --
def serve_argv(root: Path, port: int) -> list[str]:
    """The weaver's API, built from the submodule into uv's cache — never into vendor/."""
    return [
        "uvx",
        "--from",
        str(root / BACKEND),
        "--with",
        "uvicorn[standard]",
        "uvicorn",
        "okf_weaver.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]


# -------------------------------------------------------------------- cli --
def register_commands(app: Any) -> None:
    """`pf tool okf build|check|weave|serve|doctor`."""
    import typer
    from rich.console import Console

    console = Console()
    okf_app = typer.Typer(help="OKF: the semantic layer as a portable, validated knowledge bundle.")

    def _targets(group: str, project: str, all_: bool) -> list[tuple[str, str]]:
        from pf.cli import all_projects

        if all_:
            return [(g, p) for g, p, _ in all_projects()]
        if not (group and project):
            console.print("[red]give a group and project, or --all[/]")
            raise typer.Exit(1)
        return [(group, project)]

    @okf_app.command("build")
    def cmd_build(
        group: str = typer.Argument(""),
        project: str = typer.Argument(""),
        all_: bool = typer.Option(False, "--all", help="every project"),
        platform: bool = typer.Option(False, "--platform", help="the platform ontology's own bundle"),
    ) -> None:
        """Regenerate a project's `okf/` from its semantic layer; `--platform` for `platform/okf/`."""
        from pf.cli import root
        from pf.projections.okf import write_platform, write_project

        if platform:
            r = write_platform(root())
            console.print(
                f"[green]✓[/] platform/okf  [dim]{r['concepts']} concept(s), {r['roles']} role(s), "
                f"{r['written']} written, {r['removed']} removed[/]"
            )
            if not (all_ or (group and project)):
                return
        for g, p in _targets(group, project, all_):
            r = write_project(root(), g, p)
            console.print(
                f"[green]✓[/] {g}/{p}  [dim]{r['tables']} table(s), {r['concepts']} concept(s), "
                f"{r['metrics']} metric(s), {r['written']} written, {r['removed']} removed[/]"
            )

    @okf_app.command("check")
    def cmd_check(
        group: str = typer.Argument(""),
        project: str = typer.Argument(""),
        all_: bool = typer.Option(False, "--all", help="every project, and the platform's"),
    ) -> None:
        """Is every committed bundle what the semantic layer projects, and conformant? Exits 1 otherwise."""
        from pf.cli import root
        from pf.projections.okf import check_platform, check_project

        problems = check_platform(root()) if all_ else []
        for g, p in _targets(group, project, all_):
            problems += check_project(root(), g, p)
        for x in problems:
            console.print(f"[red]✗[/] {x}")
        if problems:
            console.print("[dim]run `pf tool okf build --all --platform` to regenerate[/]")
            raise typer.Exit(1)
        console.print("[green]✓[/] every OKF bundle matches its semantic layer")

    @okf_app.command("weave")
    def cmd_weave(
        group: str,
        project: str,
        context: str = typer.Option("", "--context", help="domain notes the weaver should prefer over guessing"),
        model: str = typer.Option("", "--model", help="Claude model id; default from the weaver"),
    ) -> None:
        """Ask OKF Weaver for definitions the platform lacks; writes `okf/weave.md` as proposals."""
        from pf.cli import root

        try:
            r = weave(root(), group, project, context=context or None, model_id=model)
        except RuntimeError as exc:
            console.print(f"[red]✗[/] {exc}")
            raise typer.Exit(1) from exc
        console.print(f"[green]✓[/] {r['path']}  [dim]{r['tables']} table(s) · usage {r['usage']}[/]")

    @okf_app.command("serve")
    def cmd_serve(port: int = typer.Option(DEFAULT_PORT, "--port")) -> None:
        """Run the weaver's own API locally (docs at /docs). Built into uv's cache, never into vendor/."""
        from pf.cli import root

        argv = serve_argv(root(), port)
        console.print(f"[dim]{' '.join(argv)}[/]")
        raise typer.Exit(subprocess.call(argv))

    @okf_app.command("doctor")
    def cmd_doctor() -> None:
        h = health()
        console.print(("[green]✓[/] " if h["ok"] else "[red]✗[/] ") + h["detail"])
        raise typer.Exit(0 if h["ok"] else 1)

    app.add_typer(okf_app, name="okf")


TOOL = Tool(
    name="okf",
    title="OKF Weaver",
    summary="Open Knowledge Format: the semantic layer as portable, validated context for agents.",
    url="https://github.com/PackMaaan/okf-weaver",
    scope=frozenset({"project", "group"}),
    capability=CAPABILITY,
    default_enabled=True,
    # The projection needs only the submodule; `weave` and `serve` say what
    # else they need when asked.
    offline=True,
    requires=(),
    dbt=DbtBinding(needs_manifest=True, artefacts=("okf/index.md", "okf/tables")),
    surface=Surface(
        port=DEFAULT_PORT,
        path="/docs",
        embeddable=True,
        start=(
            "uvx",
            "--from",
            "{root}/vendor/okf-weaver/backend",
            "--with",
            "uvicorn[standard]",
            "uvicorn",
            "okf_weaver.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "{port}",
        ),
        health="/api/health",
    ),
    health="pf.tools.okf:health",
    bootstrap="pf.tools.okf:bootstrap_project",
    dagster="pf.tools.okf:dagster_assets",
    commands="pf.tools.okf:register_commands",
    stack_layer={
        "layer": "semantics",
        "title": "Knowledge (OKF)",
        "upstream": "okf-weaver",
        "toolkits": [],
        "artefacts": "okf/**",
        "node_kinds": ["Model", "Metric"],
    },
)
