"""`pf` — the platform CLI. Every justfile recipe delegates here."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from pf import obs
from pf.kg.build import build_graph
from pf.kg.card import GROUP_CARD_BUDGET, PROJECT_CARD_BUDGET, estimate_tokens, \
    render_group_card, render_project_card
from pf.kg.impact import gate, impact_of
from pf.kg.query import kg_neighbors, kg_search
from pf.ontology.model import load_ontology
from pf.ontology.validate import validate_instance, validate_project
from pf.runtime.staging import generate as generate_staging
from pf.scaffold.generator import new_group, new_project

app = typer.Typer(add_completion=False, help="Agentic data platform control CLI.")
kg_app = typer.Typer(help="Knowledge graph operations.")
app.add_typer(kg_app, name="kg")
console = Console()


def root() -> Path:
    return obs.repo_root()


def pdir(group: str, project: str) -> Path:
    p = root() / "groups" / group / "projects" / project
    if not p.exists():
        console.print(f"[red]project {group}/{project} not found[/]")
        raise typer.Exit(1)
    return p


def all_projects() -> list[tuple[str, str, Path]]:
    out = []
    gdir = root() / "groups"
    if not gdir.exists():
        return out
    for g in sorted(x for x in gdir.iterdir() if x.is_dir() and not x.name.startswith(".")):
        p_dir = g / "projects"
        if p_dir.exists():
            for p in sorted(x for x in p_dir.iterdir() if x.is_dir() and not x.name.startswith(".")):
                out.append((g.name, p.name, p))
    return out


# ------------------------------------------------------------- scaffolding --
@app.command("new-group")
def cmd_new_group(
    group: str,
    domain: str = typer.Option("b2b_saas", help="b2b_saas | ecommerce | marketplace | fintech"),
) -> None:
    """Create a new company group (a family of sister companies)."""
    files = new_group(root(), group, domain)
    render_group_card(root() / "groups" / group, group)
    console.print(f"[green]✓[/] group [bold]{group}[/] created with {len(files)} files")
    console.print(f"  next: [cyan]pf new-project {group} {group}-us[/]")


@app.command("new-project")
def cmd_new_project(
    group: str,
    project: str,
    rollup: bool = typer.Option(False, "--rollup", help="cross-entity roll-up project"),
    sisters: str = typer.Option("", help="comma-separated sister projects (roll-up only)"),
) -> None:
    """Create a project (one legal entity) inside a group."""
    sister_list = [s.strip() for s in sisters.split(",") if s.strip()]
    files = new_project(root(), group, project, is_rollup=rollup, sisters=sister_list)
    render_group_card(root() / "groups" / group, group)
    console.print(f"[green]✓[/] project [bold]{group}/{project}[/] created with {len(files)} files")
    console.print(f"  next: [cyan]pf seed {group} {project}[/] then [cyan]pf kg build {group} {project}[/]")


@app.command()
def work(group: str, project: str) -> None:
    """Launch Claude Code scoped to exactly one project."""
    d = pdir(group, project)
    console.print(f"[dim]cwd → {d}[/]")
    os.chdir(d)
    os.execvp("claude", ["claude"])


# ------------------------------------------------------------ graph & card --
@kg_app.command("build")
def cmd_kg_build(group: str, project: str) -> None:
    """Rebuild a project's knowledge graph from annotations + dbt manifests."""
    d = pdir(group, project)
    counts = build_graph(d, group=group, project=project)
    t = Table("kind", "nodes", title=f"{group}/{project} graph")
    for k, v in sorted(counts.items()):
        t.add_row(k, str(v))
    console.print(t)


@kg_app.command("card")
def cmd_kg_card(group: str, project: str) -> None:
    """Regenerate the context card (the always-in-context index)."""
    d = pdir(group, project)
    p = render_project_card(d, group, project)
    render_group_card(root() / "groups" / group, group)
    tokens = estimate_tokens(p.read_text())
    status = "green" if tokens <= PROJECT_CARD_BUDGET else "red"
    console.print(f"[{status}]✓[/] {p}  (~{tokens} tokens / {PROJECT_CARD_BUDGET} budget)")


@kg_app.command("search")
def cmd_kg_search(group: str, project: str, term: str) -> None:
    """Search the graph."""
    console.print(kg_search(pdir(group, project) / "kg" / "graph.duckdb", term))


@kg_app.command("neighbors")
def cmd_kg_neighbors(group: str, project: str, node: str, depth: int = 1) -> None:
    """Explore around a node."""
    console.print(kg_neighbors(pdir(group, project) / "kg" / "graph.duckdb", node, depth=depth))


# ---------------------------------------------------------------- impact ----
@app.command()
def impact(group: str, project: str, node: str,
           record: bool = typer.Option(True, help="write to the tracking DB")) -> None:
    """Blast radius of changing a node. The merge gate."""
    gp = pdir(group, project) / "kg" / "graph.duckdb"
    try:
        report = impact_of(gp, node)
    except KeyError:
        console.print(f"[red]node '{node}' not in graph[/]")
        console.print(kg_search(gp, node.split(":")[-1]))
        raise typer.Exit(1)
    console.print(report.render())
    if record:
        obs.record_impact(group=group, project=project, root_node=node,
                          severity=report.severity, total=report.total,
                          report=report.to_dict())
    if report.severity == "breaking":
        raise typer.Exit(1)


@app.command("impact-gate")
def cmd_impact_gate(group: str, project: str, nodes: str) -> None:
    """CI gate over a comma-separated set of changed nodes."""
    gp = pdir(group, project) / "kg" / "graph.duckdb"
    code, rendered = gate(gp, [n.strip() for n in nodes.split(",") if n.strip()])
    console.print(rendered)
    raise typer.Exit(code)


# ----------------------------------------------------------------- checks ---
@app.command()
def check(group: str = "", project: str = "") -> None:
    """Ontology conformance + card budgets across projects."""
    targets = [(g, p, d) for g, p, d in all_projects()
               if (not group or g == group) and (not project or p == project)]
    if not targets:
        console.print("[yellow]no projects found[/]")
        raise typer.Exit(0)

    failed = False
    for g, p, d in targets:
        issues = validate_project(d)
        inst = validate_instance(root() / "groups" / g / "ontology" / "instance.yaml")
        errors = [i for i in issues + inst if i.severity == "error"]
        warns = [i for i in issues + inst if i.severity == "warning"]
        mark = "[red]✗[/]" if errors else "[green]✓[/]"
        console.print(f"{mark} {g}/{p}  {len(errors)} error(s), {len(warns)} warning(s)")
        for i in errors + warns:
            console.print(f"    {i}")
        failed = failed or bool(errors)
    raise typer.Exit(1 if failed else 0)


@app.command()
def tokens(exact: bool = typer.Option(False, help="use the Anthropic count_tokens API")) -> None:
    """Enforce the always-on token budget. Fails if a card is over."""
    rows, over = [], False
    for g, p, d in all_projects():
        for artefact, path, budget in [
            ("context_card", d / "kg" / "context_card.md", PROJECT_CARD_BUDGET),
            ("project_claude", d / "CLAUDE.md", 600),
        ]:
            if not path.exists():
                continue
            text = path.read_text()
            n = _count(text, exact)
            obs.record_token_budget(group=g, project=p, artefact=artefact, tokens=n, budget=budget)
            over = over or n > budget
            rows.append((f"{g}/{p}", artefact, n, budget, "OK" if n <= budget else "OVER"))
    for g in (root() / "groups").iterdir() if (root() / "groups").exists() else []:
        card = g / "kg" / "group_card.md"
        if card.exists():
            n = _count(card.read_text(), exact)
            obs.record_token_budget(group=g.name, project="", artefact="group_card",
                                    tokens=n, budget=GROUP_CARD_BUDGET)
            over = over or n > GROUP_CARD_BUDGET
            rows.append((g.name, "group_card", n, GROUP_CARD_BUDGET,
                         "OK" if n <= GROUP_CARD_BUDGET else "OVER"))

    routing = root() / "platform" / "toolkits" / "ROUTING.md"
    if routing.exists():
        n = _count(routing.read_text(), exact)
        rows.append(("platform", "ROUTING.md", n, 400, "OK" if n <= 400 else "OVER"))
        over = over or n > 400

    t = Table("scope", "artefact", "tokens", "budget", "status", title="Always-on token budget")
    for r in rows:
        t.add_row(r[0], r[1], str(r[2]), str(r[3]), f"[green]{r[4]}[/]" if r[4] == "OK" else f"[red]{r[4]}[/]")
    console.print(t)
    total = sum(r[2] for r in rows if r[1] in ("context_card", "project_claude", "group_card", "ROUTING.md"))
    console.print(f"[dim]worst-case session preamble ≈ {total} tokens[/]")
    raise typer.Exit(1 if over else 0)


def _count(text: str, exact: bool) -> int:
    if not exact:
        return estimate_tokens(text)
    try:
        import anthropic
        client = anthropic.Anthropic()
        return client.messages.count_tokens(
            model="claude-opus-5",
            messages=[{"role": "user", "content": text}],
        ).input_tokens
    except Exception as exc:  # noqa: BLE001 — fall back to the estimate
        console.print(f"[yellow]count_tokens unavailable ({exc}); using estimate[/]")
        return estimate_tokens(text)


# ------------------------------------------------------------------ data ----
@app.command("gen-staging")
def cmd_gen_staging(group: str, project: str,
                    overwrite: bool = typer.Option(False, "--overwrite")) -> None:
    """Generate 1:1 staging models with role-driven cleaning from annotations."""
    d = pdir(group, project)
    try:
        written = generate_staging(d, overwrite=overwrite)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(1)
    if not written:
        console.print("[yellow]nothing written — pass --overwrite to regenerate[/]")
        return
    for p in written:
        console.print(f"  [green]+[/] {p.relative_to(d)}")
    console.print(f"[green]✓[/] {len(written)} file(s)")


@app.command()
def seed(group: str, project: str) -> None:
    """Run the project's pipelines and dbt build, then rebuild graph + card."""
    d = pdir(group, project)
    module = project.replace("-", "_")
    seed_script = d / "src" / module / "seed.py"
    if seed_script.exists():
        console.print(f"[dim]running {seed_script}[/]")
        r = subprocess.run([sys.executable, str(seed_script)], cwd=str(d))
        if r.returncode:
            raise typer.Exit(r.returncode)
    else:
        console.print("[yellow]no seed.py — skipping data load[/]")
    cmd_kg_build(group, project)
    cmd_kg_card(group, project)


@app.command("run-all")
def run_all(group: str) -> None:
    """Run every sister project in parallel, then the roll-up."""
    sisters = [(g, p, d) for g, p, d in all_projects() if g == group and not p.endswith("-rollup")]
    rollups = [(g, p, d) for g, p, d in all_projects() if g == group and p.endswith("-rollup")]
    procs = []
    for g, p, d in sisters:
        console.print(f"[cyan]▸[/] launching {g}/{p}")
        procs.append((p, subprocess.Popen(
            [sys.executable, "-m", "pf.cli", "seed", g, p], cwd=str(root()))))
    failed = False
    for name, proc in procs:
        rc = proc.wait()
        console.print(f"  {'[green]✓[/]' if rc == 0 else '[red]✗[/]'} {name}")
        failed = failed or rc != 0
    for g, p, d in rollups:
        console.print(f"[cyan]▸[/] roll-up {g}/{p}")
        seed(g, p)
    raise typer.Exit(1 if failed else 0)


@app.command()
def status() -> None:
    """Show every group and project."""
    t = Table("group", "project", "warehouse", "graph nodes", "card tokens")
    for g, p, d in all_projects():
        wh = d / "data"
        dbs = list(wh.glob("*.duckdb")) if wh.exists() else []
        gp = d / "kg" / "graph.duckdb"
        n = "—"
        if gp.exists():
            from pf.kg.store import open_graph
            with open_graph(gp, read_only=True) as gr:
                n = str(sum(gr.counts().values()))
        card = d / "kg" / "context_card.md"
        ct = str(estimate_tokens(card.read_text())) if card.exists() else "—"
        t.add_row(g, p, dbs[0].name if dbs else "—", n, ct)
    console.print(t)


@app.command()
def ontology() -> None:
    """Print the platform ontology."""
    o = load_ontology()
    t = Table("class", "parent", "abstract", "description", title=f"Ontology v{o.version}")
    for c in o.classes.values():
        t.add_row(c.name, c.parent or "", "yes" if c.abstract else "", c.description)
    console.print(t)
    console.print(f"[dim]roles: {', '.join(o.roles)}[/]")


@app.command("dagster-workspace")
def cmd_dagster_workspace() -> None:
    """Generate platform/workspace.yaml — one code location per project.

    Paths are absolute: Dagster resolves a relative `working_directory` against
    the process cwd, not against the workspace file, so a relative path silently
    resolves outside the repo.
    """
    r = root()
    lines = [
        "# GENERATED by `pf dagster-workspace`. Re-run after adding a project.",
        "#",
        "# One code location per project: a failure or reload in one sister never",
        "# affects another, and each gets its own process.",
        "load_from:",
    ]
    for g, p, d in all_projects():
        module = p.replace("-", "_")
        if not (d / "src" / module / "definitions.py").exists():
            continue
        lines += [
            "  - python_module:",
            f"      module_name: {module}.definitions",
            f"      working_directory: {(d / 'src').resolve()}",
            f"      location_name: {g}__{p}",
        ]
    out = r / "platform" / "workspace.yaml"
    out.write_text("\n".join(lines) + "\n")
    n = sum(1 for line in lines if line.startswith("  - python_module"))
    console.print(f"[green]✓[/] {out}  ({n} code location(s))")
    console.print(f"  run: [cyan]DAGSTER_HOME={r}/.dagster uv run dagster dev "
                  f"-w platform/workspace.yaml[/]")


@app.command()
def ui(host: str = "127.0.0.1", port: int = 8787) -> None:
    """Serve the control-plane dashboard."""
    from pf.ui.app import serve
    console.print(f"[green]Control plane →[/] http://{host}:{port}")
    serve(host, port)


@app.command()
def mcp() -> None:
    """Run the MCP server over stdio."""
    from pf.mcp.server import main
    main()


if __name__ == "__main__":
    app()
