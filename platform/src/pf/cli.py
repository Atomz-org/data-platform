"""`pf` — the platform CLI. Every justfile recipe delegates here."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

from pf import obs
from pf.agents.base import AGENTS, validate_routing
from pf.agents.models import MODELS
from pf.capabilities import (
    CAPABILITIES, UnknownCapability, apply as apply_capability, gate_additions,
    missing_env, resolve as resolve_capabilities,
)
from pf.kg.build import build_graph
from pf.kg.card import GROUP_CARD_BUDGET, PROJECT_CARD_BUDGET, estimate_tokens, \
    render_group_card, render_project_card
from pf.kg.impact import gate, impact_of, impact_of_many
from pf.kg.query import kg_neighbors, kg_search
from pf.ontology.model import load_ontology
from pf.ontology.validate import validate_instance, validate_project, validate_topology
from pf.runtime.staging import generate as generate_staging
from pf.loops.audit import audit as loop_audit, project_readiness, recommended_level
from pf.loops.gate import GateResult, check_paths, nodes_for, project_for, tracked_denied
from pf.loops.registry import BODIES, SPECS
from pf.loops.runner import Ledger, run_loop, update_state
from pf.scaffold.bootstrap import STEPS, bootstrap
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
    from pf.context import build as build_context

    files = new_group(root(), group, domain)
    render_group_card(root() / "groups" / group, group)
    # The toolkit index is platform-wide, so a group with no projects yet still
    # needs it present — `pf work <group>` sessions read it before any project
    # exists to bootstrap.
    build_context(root())
    console.print(f"[green]✓[/] group [bold]{group}[/] created with {len(files)} files")
    console.print(f"  next: [cyan]pf new-project {group} {group}-us[/]")


@app.command("new-project")
def cmd_new_project(
    group: str,
    project: str,
    rollup: bool = typer.Option(False, "--rollup", help="cross-entity roll-up project"),
    sisters: str = typer.Option("", help="comma-separated sister projects (roll-up only)"),
    with_: str = typer.Option("", "--with", help="comma-separated capabilities "
                                                 "(see `pf capabilities`)"),
) -> None:
    """Create a project (one legal entity) inside a group.

    One command, everything wired: scaffold, knowledge graph, group card,
    optional capabilities, gate rules, and the Dagster code location. Nothing
    here is a follow-up step you can forget — a half-registered project is how a
    gate ends up inert.
    """
    sister_list = [s.strip() for s in sisters.split(",") if s.strip()]
    names = [c.strip() for c in with_.split(",") if c.strip()]
    try:
        caps = resolve_capabilities(names)
    except (UnknownCapability, ValueError) as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(1)

    files = new_project(root(), group, project, is_rollup=rollup, sisters=sister_list)
    render_group_card(root() / "groups" / group, group)
    d = root() / "groups" / group / "projects" / project

    ctx = {"group": group, "project": project, "module": project.replace("-", "_")}
    for cap in caps:
        written = apply_capability(cap, root(), d, ctx)
        console.print(f"  [green]+[/] capability [bold]{cap.name}[/] "
                      f"({len(written)} file(s))")
    if caps:
        _merge_gate_rules(gate_additions(caps))

    # Everything past the file writes lives in `pf.scaffold.bootstrap`, shared
    # with `pf bootstrap`. Inlining it here is what previously left projects
    # created before a capability landed permanently missing it.
    console.print(f"[green]✓[/] project [bold]{group}/{project}[/] created with {len(files)} files")
    _print_bootstrap(bootstrap(root(), group, project))
    if caps:
        console.print(f"  [dim]capabilities: {', '.join(c.name for c in caps)}[/]")
    for cap, missing in missing_env(caps).items():
        console.print(f"  [yellow]![/] {cap} needs unset env: {', '.join(missing)}")
    console.print(f"  next: [cyan]pf seed {group} {project}[/] · [cyan]pf loop audit[/]")


def _merge_gate_rules(additions: dict[str, list[str]]) -> None:
    """Append capability-contributed patterns to the generated gate overlay.

    Written to `gate.capabilities.yaml`, never to `gate.yaml`: round-tripping the
    hand-written policy through the YAML dumper strips every comment in it, and
    those comments are where each rule's reason lives. `load_policy` unions the
    two. Appends only — a capability may tighten the gate, never loosen it.
    """
    if not additions:
        return
    path = root() / "gate.capabilities.yaml"
    existing = yaml.safe_load(path.read_text()) if path.exists() else {}
    existing = existing or {}
    changed = []
    for section, patterns in additions.items():
        bucket = existing.setdefault(section, [])
        for p in patterns:
            if p not in bucket:
                bucket.append(p)
                changed.append(f"{section}:{p}")
    if changed:
        path.write_text(
            "# GENERATED by `pf new-project --with`. Merged over gate.yaml at load\n"
            "# time by pf.loops.gate.load_policy. Edit the capability, not this file.\n"
            + yaml.safe_dump(existing, sort_keys=False))
        console.print(f"  [dim]gate overlay += {', '.join(changed)}[/]")


@app.command("context")
def cmd_context(group: str = typer.Argument(""), project: str = typer.Argument("")) -> None:
    """Rebuild the toolkit index and capability cards.

    Also run by `pf bootstrap`, so this is only needed after editing a toolkit's
    CONTEXT.md or a Capability declaration and wanting the result immediately.
    """
    from pf.context import (
        TOOLKIT_INDEX_BUDGET, TOOLS_CARD_BUDGET, build, problems,
    )

    for line in problems(root()):
        console.print(f"  [yellow]![/] unparseable frontmatter — contributes nothing: {line}")

    targets = [(group, project)] if group and project else [
        (g, p) for g, p, _ in all_projects()]
    written: list[Path] = []
    for g, p in targets:
        written += build(root(), g, p)

    for path in dict.fromkeys(written):
        budget = TOOLKIT_INDEX_BUDGET if path.name == "TOOLKITS.md" else TOOLS_CARD_BUDGET
        n = estimate_tokens(path.read_text())
        mark = "[green]✓[/]" if n <= budget else "[red]✗[/]"
        console.print(f"  {mark} {path.relative_to(root())} [dim]{n}/{budget} tokens[/]")


@app.command()
def capabilities() -> None:
    """Optional features `pf new-project --with` can wire into a project."""
    t = Table("capability", "adds", "needs env", "description")
    for c in CAPABILITIES.values():
        t.add_row(c.name, f"{len(c.files)} file(s)",
                  ", ".join(c.env) or "—", c.description)
    console.print(t)
    console.print("[dim]Adding one is a single entry in pf.capabilities.CAPABILITIES — "
                  "it does not touch the scaffolder, the CLI, or the gate.[/]")


@app.command()
def models() -> None:
    """Model routing per step, with what each model actually accepts."""
    t = Table("step", "model", "effort", "thinking", "cache", "$/Mtok in/out",
              title="Agent routing")
    for cfg in AGENTS.values():
        s = MODELS.get(cfg.model)
        if s is None:
            t.add_row(cfg.name, f"[red]{cfg.model} (unknown)[/]", "—", "—", "—", "—")
            continue
        effort = cfg.effort if s.supports_effort else "[dim]n/a[/]"
        thinking = ("adaptive" if s.thinking == "adaptive" and cfg.thinking
                    else "budget" if s.thinking == "budget" and cfg.thinking else "off")
        t.add_row(cfg.name, s.id, effort, thinking,
                  f"≥{s.cache_min_tokens} tok", f"{s.usd_in:.2f}/{s.usd_out:.2f}")
    console.print(t)
    for cfg in AGENTS.values():
        if cfg.purpose:
            console.print(f"  [dim]{cfg.name}: {cfg.purpose}[/]")
    issues = validate_routing()
    for i in issues:
        console.print(f"  [yellow]![/] {i}")
    if not issues:
        console.print("[green]✓[/] every routed step matches its model's capabilities")


@app.command("capability-add")
def cmd_capability_add(capability: str, group: str, project: str) -> None:
    """Add a capability to an existing project, then bootstrap it.

    Capabilities were previously opt-in only at creation, which meant a project
    made before one existed could never get it — the same hole `pf bootstrap`
    closed for platform steps.
    """
    try:
        caps = resolve_capabilities([capability])
    except (UnknownCapability, ValueError) as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(1)

    d = pdir(group, project)
    ctx = {"group": group, "project": project, "module": project.replace("-", "_")}
    for cap in caps:
        written = apply_capability(cap, root(), d, ctx)
        console.print(f"  [green]+[/] {cap.name} ({len(written)} file(s))")
    _merge_gate_rules(gate_additions(caps))
    _print_bootstrap(bootstrap(root(), group, project))


@app.command("bootstrap")
def bootstrap_cmd(
    group: str = typer.Argument("", help="group (omit with --all)"),
    project: str = typer.Argument("", help="project (omit with --all)"),
    all_: bool = typer.Option(False, "--all", help="every project in the repo"),
) -> None:
    """Re-run every post-scaffold step. Idempotent.

    Run this after upgrading the platform: a project created before a capability
    existed gets it here, rather than by hand-patching.
    """
    targets = all_projects() if all_ else [(group, project, pdir(group, project))]
    if not all_ and not (group and project):
        console.print("[red]give a group and project, or --all[/]")
        raise typer.Exit(1)

    failed = False
    for g, p, _ in targets:
        console.print(f"[bold]{g}/{p}[/]")
        results = _print_bootstrap(bootstrap(root(), g, p))
        failed = failed or not results
    raise typer.Exit(1 if failed else 0)


def _print_bootstrap(results) -> bool:
    ok = True
    for r in results:
        mark = {"ok": "[green]✓[/]", "skipped": "[dim]·[/]", "failed": "[red]✗[/]"}[r.status]
        console.print(f"  {mark} {r.name:24} [dim]{r.detail}[/]")
        ok = ok and r.ok
    return ok


@app.command("bootstrap-steps")
def cmd_bootstrap_steps() -> None:
    """What `pf bootstrap` does, and why each step exists."""
    t = Table("step", "why")
    for s in STEPS:
        t.add_row(s.name, s.why)
    console.print(t)


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
def check(group: str = "", project: str = "",
          impact: bool = typer.Option(True, help="also gate on blast radius of changes")) -> None:
    """Ontology conformance, and the blast radius of anything you have changed."""
    targets = [(g, p, d) for g, p, d in all_projects()
               if (not group or g == group) and (not project or p == project)]
    if not targets:
        console.print("[yellow]no projects found[/]")
        raise typer.Exit(0)

    # Before anything project-specific: does git agree with the gate about what
    # is generated? When it does not, every later diff is polluted with files
    # nobody edited, and a reviewer stops reading them.
    tracked = tracked_denied(root())
    if tracked:
        console.print(f"[red]✗[/] tracked artefacts  {len(tracked)} file(s) git is "
                      f"tracking that the gate calls generated")
        for r in tracked[:8]:
            console.print(f"    [red]{r.path}[/] [dim]({r.rule})[/]")
        if len(tracked) > 8:
            console.print(f"    [dim]…and {len(tracked) - 8} more[/]")
        console.print("    [dim]git rm --cached <paths>, then add the pattern to "
                      ".gitignore[/]")
    else:
        console.print("[green]✓[/] tracked artefacts  git and gate.yaml agree")

    # Generated context that has stopped matching what it is generated from is
    # believed by every agent that reads it — the same failure the tracked-artefact
    # check exists for, one layer up.
    from pf.context import is_stale, problems as context_problems

    broken = context_problems(root())
    for line in broken:
        console.print(f"[yellow]![/] unparseable frontmatter, contributes no rules: {line}")
    stale = [f"{g}/{p}" for g, p, _ in targets if is_stale(root(), g, p)]
    if stale:
        console.print(f"[red]✗[/] context artefacts  stale for {', '.join(stale)}")
        console.print("    [dim]run `pf context`[/]")
    else:
        console.print("[green]✓[/] context artefacts  toolkit index and capability "
                      "cards match their sources")

    topo = validate_topology()
    topo_errors = [i for i in topo if i.severity == "error"]
    mark = "[red]✗[/]" if topo_errors else "[green]✓[/]"
    console.print(f"{mark} ontology + topology  {len(topo_errors)} error(s), "
                  f"{len(topo) - len(topo_errors)} warning(s)")
    for i in topo:
        console.print(f"    {i}")

    failed = bool(topo_errors) or bool(tracked) or bool(stale)
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

        if impact:
            failed = _impact_on_changes(g, p, d) or failed
    raise typer.Exit(1 if failed else 0)


def _impact_on_changes(group: str, project: str, d: Path) -> bool:
    """Blast radius of every uncommitted change to models or sources.

    This is the gate that makes impact analysis structural rather than a rule an
    agent has to remember. It was written after a session in which the agent
    regenerated staging models, broke three marts, and never ran the gate it had
    built for exactly that failure.
    """
    changed = _changed_nodes(d)
    if not changed:
        return False
    gp = d / "kg" / "graph.duckdb"
    if not gp.exists():
        console.print("    [yellow]graph not built; cannot assess impact[/]")
        return False
    report = impact_of_many(gp, changed)
    if report.total == 0:
        console.print(f"    [green]✓[/] {len(changed)} changed node(s), no downstream impact")
        return False
    console.print(f"    [dim]changed:[/] {', '.join(changed)}")
    for line in report.render().splitlines():
        console.print(f"    {line}")
    obs.record_impact(group=group, project=project,
                      root_node=",".join(changed), severity=report.severity,
                      total=report.total, report=report.to_dict())
    return report.severity == "breaking"


def _changed_nodes(project_dir: Path) -> list[str]:
    """Graph node ids for models/sources touched in the working tree."""
    proc = subprocess.run(["git", "status", "--porcelain", "--", str(project_dir)],
                          capture_output=True, text=True, cwd=str(root()))
    nodes: list[str] = []
    for line in proc.stdout.splitlines():
        path = line[3:].strip().strip('"')
        p = Path(path)
        if p.suffix == ".sql" and "models" in p.parts:
            nodes.append(f"model:{p.stem}")
        elif p.suffix == ".py" and "sources" in p.parts:
            nodes.append(f"source:{p.stem}")
    return sorted(set(nodes))


@app.command()
def tokens(exact: bool = typer.Option(False, help="use the Anthropic count_tokens API")) -> None:
    """Enforce the always-on token budget. Fails if a card is over."""
    rows, over = [], False
    for g, p, d in all_projects():
        from pf.context import TOOLS_CARD_BUDGET

        for artefact, path, budget in [
            ("context_card", d / "kg" / "context_card.md", PROJECT_CARD_BUDGET),
            ("project_claude", d / "CLAUDE.md", 600),
            ("tools_card", d / "kg" / "tools_card.md", TOOLS_CARD_BUDGET),
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

    from pf.context import TOOLKIT_INDEX, TOOLKIT_INDEX_BUDGET

    index = root() / TOOLKIT_INDEX
    if index.exists():
        n = _count(index.read_text(), exact)
        rows.append(("platform", "TOOLKITS.md", n, TOOLKIT_INDEX_BUDGET,
                     "OK" if n <= TOOLKIT_INDEX_BUDGET else "OVER"))
        over = over or n > TOOLKIT_INDEX_BUDGET

    from pf.vendor.card import VENDOR_CARD_BUDGET

    vcard = root() / "docs" / "VENDOR-CARD.md"
    if vcard.exists():
        n = _count(vcard.read_text(), exact)
        rows.append(("platform", "VENDOR-CARD.md", n, VENDOR_CARD_BUDGET,
                     "OK" if n <= VENDOR_CARD_BUDGET else "OVER"))
        over = over or n > VENDOR_CARD_BUDGET

    t = Table("scope", "artefact", "tokens", "budget", "status", title="Always-on token budget")
    for r in rows:
        t.add_row(r[0], r[1], str(r[2]), str(r[3]), f"[green]{r[4]}[/]" if r[4] == "OK" else f"[red]{r[4]}[/]")
    console.print(t)
    total = sum(r[2] for r in rows if r[1] in ("context_card", "project_claude", "group_card",
                                               "ROUTING.md", "TOOLKITS.md", "tools_card"))
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


# ------------------------------------------------------------------ loops --
loop_app = typer.Typer(help="Loop engineering: scheduled, gated, budgeted agent work.")
app.add_typer(loop_app, name="loop")


@loop_app.command("list")
def cmd_loop_list() -> None:
    """Every loop, with its autonomy level and budget."""
    t = Table("loop", "autonomy", "cadence", "budget", "writes", "description")
    for s in SPECS.values():
        t.add_row(s.name, s.autonomy, s.cadence,
                  f"{s.token_budget:,}" if s.token_budget else "—",
                  "yes" if s.writes else "no", s.description)
    console.print(t)
    console.print("[dim]L1 report-only · L2 gated patches · L3 unattended. "
                  "Nothing is L3 until it has a track record.[/]")


@loop_app.command("run")
def cmd_loop_run(loop: str, group: str, project: str,
                 dry_run: bool = typer.Option(False, "--dry-run")) -> None:
    """Run one loop against one project."""
    spec = SPECS.get(loop)
    if spec is None:
        console.print(f"[red]unknown loop '{loop}'[/]. Try: {', '.join(SPECS)}")
        raise typer.Exit(1)
    d = pdir(group, project)
    r = root()
    run = run_loop(spec, lambda run: BODIES[loop](r, group, project, run),
                   root=r, group=group, project=project, dry_run=dry_run)
    colour = {"ok": "yellow", "noop": "green", "circuit_open": "red",
              "error": "red", "escalated": "red"}.get(run.outcome, "white")
    console.print(f"[{colour}]{run.outcome}[/] {loop} · {group}/{project} "
                  f"· {run.duration_ms}ms · attempt {run.attempt}")
    if run.message:
        console.print(f"  [dim]{run.message}[/]")
    for f in run.findings:
        console.print(f"  • {f}")
    if not run.findings and run.outcome == "noop":
        console.print("  [dim]nothing to report[/]")


@loop_app.command("run-all")
def cmd_loop_run_all(group: str, project: str) -> None:
    """Run every read-only (L1) loop and refresh STATE.md."""
    r, findings = root(), []
    for name, spec in SPECS.items():
        if spec.autonomy != "L1":
            continue
        run = run_loop(spec, lambda run, n=name: BODIES[n](r, group, project, run),
                       root=r, group=group, project=project)
        for f in run.findings:
            findings.append(f"[{name}] {f}")
        console.print(f"  {'[yellow]•[/]' if run.findings else '[green]✓[/]'} "
                      f"{name}: {len(run.findings)} finding(s)")
    p = update_state(r, findings, watch=[s.name for s in SPECS.values() if s.autonomy != "L1"])
    console.print(f"[green]✓[/] {p} updated ({len(findings)} open item(s))")


@loop_app.command("audit")
def cmd_loop_audit() -> None:
    """Loop Readiness Score — is this repo safe to give a loop more autonomy?"""
    score, checks = loop_audit(root())
    t = Table("check", "weight", "status", "detail", title="Loop Readiness")
    for c in checks:
        t.add_row(c.name, str(c.weight),
                  "[green]PASS[/]" if c.passed else "[red]FAIL[/]", c.detail)
    console.print(t)

    rows = project_readiness(root())
    pt = Table("group/project", "hook", "graph", "card", "CLAUDE.md", "state",
               title="Per-project governance")
    tick = {True: "[green]✓[/]", False: "[red]✗[/]"}
    for r in rows:
        pt.add_row(f"{r.group}/{r.project}", tick[r.hook], tick[r.graph], tick[r.card],
                   tick[r.claude_md],
                   "[green]ready[/]" if r.ready else f"[red]missing: {', '.join(r.missing)}[/]")
    console.print(pt)
    if any(not r.ready for r in rows):
        console.print("[yellow]A project without a graph is ungoverned: its edits get a "
                      "warning, never a blast radius. Run `pf kg build <group> <project>`.[/]")
    colour = "green" if score >= 80 else "yellow" if score >= 55 else "red"
    console.print(f"[{colour}]Score: {score}/100[/] — {recommended_level(score, root())}")
    raise typer.Exit(0 if score >= 55 else 1)


@loop_app.command("status")
def cmd_loop_status(limit: int = 15) -> None:
    """Recent loop runs from the ledger."""
    entries = Ledger(root()).read()[-limit:]
    if not entries:
        console.print("[yellow]no runs yet[/]")
        return
    t = Table("when", "loop", "project", "outcome", "findings", "ms")
    for e in entries:
        t.add_row(e["started_at"][:19], e["loop"], e["project"], e["outcome"],
                  str(len(e.get("findings") or [])), str(e.get("duration_ms", 0)))
    console.print(t)


@loop_app.command("reset")
def cmd_loop_reset(loop: str, group: str, project: str,
                   note: str = typer.Option("", help="why it is safe to resume")) -> None:
    """Clear a latched circuit breaker after resolving the underlying finding."""
    if loop not in SPECS:
        console.print(f"[red]unknown loop '{loop}'[/]. Try: {', '.join(SPECS)}")
        raise typer.Exit(1)
    pdir(group, project)
    ledger = Ledger(root())
    fails = ledger.consecutive_failures(loop, project)
    if not fails:
        console.print(f"[green]✓[/] {loop} · {group}/{project} is not tripped")
        return
    ledger.reset(loop, group, project, note)
    console.print(f"[green]✓[/] {loop} · {group}/{project} reset "
                  f"({fails} consecutive failure(s) cleared)")


@app.command()
def gate(paths: str = typer.Option(..., help="comma-separated paths")) -> None:
    """Enforce gate.yaml over a set of paths. Used by the pre-commit hook."""
    from pf.kg.impact import impact_of_many

    r = root()
    plist = [p.strip() for p in paths.split(",") if p.strip()]
    results = check_paths(plist, r, in_project=False)
    blocked = [x for x in results if x.blocked]
    warned = [x for x in results if x.verdict == "warn"]

    for x in blocked:
        console.print(f"[red]DENY[/] {x.path}  [{x.rule}]  {x.message}")

    by_project: dict[tuple[str, str, Path], list[str]] = {}
    for x in warned:
        proj = project_for(x.path, r)
        if proj:
            by_project.setdefault(proj, []).extend(nodes_for(x.path))
    for (g, p, d), nodes in by_project.items():
        gp = d / "kg" / "graph.duckdb"
        if not gp.exists() or not nodes:
            continue
        rep = impact_of_many(gp, sorted(set(nodes)))
        if rep.total:
            console.print(f"[yellow]IMPACT[/] {g}/{p}")
            for line in rep.render().splitlines():
                console.print(f"  {line}")
            if rep.severity == "breaking":
                blocked.append(GateResult("deny", "impact:breaking", f"{g}/{p}",
                                          f"{rep.total} downstream object(s)"))

    if blocked:
        console.print("\n[red]blocked[/] — resolve, or commit with --no-verify "
                      "and say why in the message")
        raise typer.Exit(1)
    console.print(f"[green]✓[/] gate passed ({len(plist)} path(s))")


# ------------------------------------------------------- semantic layer --
sem_app = typer.Typer(help="Ontology, topology and their projections.")
app.add_typer(sem_app, name="semantic")


@sem_app.command("scan")
def cmd_onto_scan(group: str, project: str,
                  schema: str = typer.Option("", help="warehouse schema (default: the dlt dataset)"),
                  source: str = typer.Option("", help="label for the proposal")) -> None:
    """Scan what a source actually landed and induce an ontology proposal."""
    from pf.ontology import induct, proposal
    from pf.ontology.model import load_group_ontology

    d = pdir(group, project)
    wh = d / "data" / f"{project.replace('-', '_')}.duckdb"
    if not wh.exists():
        console.print(f"[red]no warehouse at {wh}[/] — run `pf seed {group} {project}` first")
        raise typer.Exit(1)

    schemas = [schema] if schema else _dlt_schemas(wh)
    if not schemas:
        console.print("[yellow]no source schemas found[/]")
        raise typer.Exit(1)

    tables = []
    for s in schemas:
        tables.extend(induct.scan(wh, s))
    if not tables:
        console.print("[yellow]nothing to scan[/]")
        raise typer.Exit(1)

    onto = load_group_ontology(root(), group)
    axioms = induct.induce(tables, set(onto.classes))
    p = proposal.create(root(), group, project, source or schemas[0], axioms)

    t = Table("kind", "proposed", "pre-accepted")
    for kind in ("class", "identity", "property", "relation"):
        total = sum(1 for a in p.axioms if a["kind"] == kind)
        acc = sum(1 for a in p.axioms if a["kind"] == kind and a["accept"])
        t.add_row(kind, str(total), str(acc))
    console.print(t)
    console.print(f"[green]✓[/] proposal [bold]{p.pid}[/] "
                  f"({len(tables)} table(s) scanned across {', '.join(schemas)})")
    console.print(f"  [dim]{proposal.path_for(root(), group, p.pid)}[/]")
    console.print(f"  Nothing is in effect yet. Review, edit, then approve:")
    console.print(f"    [cyan]pf semantic review {group} {p.pid}[/]")
    console.print(f"    [cyan]pf semantic approve {group} {p.pid}[/]")


def _dlt_schemas(warehouse: Path) -> list[str]:
    """Schemas that look like dlt datasets, not dbt output."""
    import duckdb

    con = duckdb.connect(str(warehouse), read_only=True)
    try:
        rows = con.execute(
            "SELECT DISTINCT table_schema FROM information_schema.tables "
            "WHERE table_schema NOT IN ('information_schema','pg_catalog','main') "
            "AND table_schema NOT LIKE 'main_%' "
            # dlt writes a parallel <dataset>_staging schema during merge loads.
            # Scanning it duplicates every class with an identical, meaningless twin.
            "AND table_schema NOT LIKE '%_staging' ORDER BY 1").fetchall()
    finally:
        con.close()
    return [r[0] for r in rows]


@sem_app.command("proposals")
def cmd_onto_proposals(group: str) -> None:
    """Every ontology proposal for a group."""
    from pf.ontology import proposal

    items = proposal.listing(root(), group)
    if not items:
        console.print("[yellow]none[/] — run `pf semantic scan <group> <project>`")
        return
    t = Table("id", "status", "source", "axioms", "accepted", "approved by")
    for p in items:
        t.add_row(p.pid, p.status, p.source, str(len(p.axioms)),
                  str(len(p.accepted)), p.approved_by or "—")
    console.print(t)


@sem_app.command("review")
def cmd_onto_review(group: str, pid: str, show: str = typer.Option(
        "accepted", help="accepted | all | rejected")) -> None:
    """What a proposal would change, and what it unlocks."""
    from pf.ontology import proposal

    p = proposal.read(root(), group, pid)
    d = proposal.diff_against(root(), group, p)

    console.print(f"[bold]{p.pid}[/]  status={p.status}  source={p.source}  "
                  f"{len(p.accepted)}/{len(p.axioms)} accepted")
    console.print()
    for label, items in (("new classes", d["new_classes"]),
                         ("reused existing classes", d["reused_classes"]),
                         ("new properties", d["new_properties"]),
                         ("new relations", d["new_relations"])):
        if items:
            console.print(f"  [bold]{label}[/] ({len(items)})")
            for i in items[:12]:
                console.print(f"    • {i}")
            if len(items) > 12:
                console.print(f"    … {len(items) - 12} more")
    console.print()

    rows = p.accepted if show == "accepted" else (
        p.axioms if show == "all" else [a for a in p.axioms if not a.get("accept")])
    t = Table("✓", "kind", "subject", "conf", "evidence", "rationale")
    for a in rows[:40]:
        t.add_row("✓" if a.get("accept") else "·", a["kind"], a["subject"],
                  a.get("confidence", ""), (a.get("evidence") or "")[:44],
                  (a.get("rationale") or "")[:60])
    console.print(t)
    if len(rows) > 40:
        console.print(f"  [dim]… {len(rows) - 40} more — read the YAML[/]")
    console.print(f"\n  Edit: [cyan]{proposal.path_for(root(), group, pid)}[/]")
    console.print(f"  Then: [cyan]pf semantic approve {group} {pid}[/]")


@sem_app.command("approve")
def cmd_onto_approve(group: str, pid: str,
                     by: str = typer.Option("", help="steward name for the audit trail"),
                     yes: bool = typer.Option(False, "--yes", help="skip confirmation")) -> None:
    """Merge accepted axioms into the group extension, then rebuild everything."""
    from pf.ontology import proposal

    p = proposal.read(root(), group, pid)
    d = proposal.diff_against(root(), group, p)
    console.print(f"About to add: {len(d['new_classes'])} class(es), "
                  f"{len(d['new_properties'])} property(ies), "
                  f"{len(d['new_relations'])} relation(s) to "
                  f"[bold]groups/{group}/ontology/extension.yaml[/]")
    if not yes and not typer.confirm("Approve?"):
        console.print("[yellow]not approved[/]")
        raise typer.Exit(1)

    try:
        p, ext_path, applied = proposal.approve(root(), group, pid, by=by)
    except ValueError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(1)

    console.print(f"[green]✓[/] approved by {p.approved_by} at {p.approved_at}")
    console.print(f"  {ext_path}: " + ", ".join(f"{v} {k}" for k, v in applied.items() if v))

    # An approved term that has not reached the graph is not yet usable by dbt,
    # Wren, the BI layer or an agent. Propagation is part of approval.
    for g, proj, _ in all_projects():
        if g == group:
            console.print(f"  [dim]propagating → {g}/{proj}[/]")
            _print_bootstrap(bootstrap(root(), g, proj))


@sem_app.command("topology")
def cmd_topology() -> None:
    """The named relations between ontology classes."""
    o = load_ontology()
    t = Table("relation", "domain", "→", "range", "cardinality", "inverse",
              title=f"Topology v{o.version}")
    for r in o.relations:
        t.add_row(r.name, r.domain, r.label or "→", r.range, r.cardinality, r.inverse or "—")
    console.print(t)


@sem_app.command("policy")
def cmd_policy() -> None:
    """Policy chain: intent → constraint → artifact → evidence."""
    o = load_ontology()
    t = Table("policy", "severity", "constraint", "enforced by", "evidence")
    for p in o.policies:
        t.add_row(p.id, p.severity, p.constraint,
                  "\n".join(p.enforced_by) or "[red]NOTHING[/]",
                  "\n".join(p.evidence) or "—")
    console.print(t)
    un = o.unenforced_policies()
    if un:
        console.print(f"[red]{len(un)} unenforced policy(ies):[/] "
                      + ", ".join(p.id for p in un))
    else:
        console.print("[green]every policy names an enforcing artifact[/]")


@sem_app.command("mdl")
def cmd_mdl(group: str, project: str,
            out: str = typer.Option("", help="output path (default <project>/mdl/mdl.json)")) -> None:
    """Export a WrenAI MDL manifest from the graph."""
    from pf.projections.mdl import export as export_mdl

    d = pdir(group, project)
    path = export_mdl(d, group, project, out or None)
    payload = json.loads(path.read_text())
    console.print(f"[green]✓[/] {path}")
    console.print(f"  models={len(payload['models'])} "
                  f"relationships={len(payload['relationships'])} "
                  f"cubes={len(payload['cubes'])}")
    for r in payload["relationships"]:
        console.print(f"  [dim]{r['joinType']}[/] {r['condition']}")


@sem_app.command("owl")
def cmd_owl(out: str = typer.Option("", help="output path")) -> None:
    """Export the ontology as OWL / RDF-XML."""
    from pf.projections.owl import export as export_owl, stats

    path = export_owl(out or (root() / "platform" / "src" / "pf" / "ontology" / "ontology.owl"))
    s = stats()
    console.print(f"[green]✓[/] {path}")
    console.print(f"  classes={s['classes']} datatypeProperties={s['datatype_properties']} "
                  f"objectProperties={s['object_properties']}")


@sem_app.command("otop")
def cmd_otop(group: str = typer.Argument("", help="omit for a platform-wide export"),
             project: str = typer.Argument(""),
             out: str = typer.Option("", help="output path")) -> None:
    """Export the policy layer as an OpenTopology (otop-core 0.2) manifest."""
    from pf.projections.otop import export as export_otop, build_manifest, stats

    d = pdir(group, project) if group and project else None
    path = export_otop(root(), group, project, d, out or None)
    s = stats(build_manifest(root(), group, project, d))
    console.print(f"[green]✓[/] {path}")
    console.print(f"  intents={s.get('intent', 0)} constraints={s.get('constraint', 0)} "
                  f"artifacts={s.get('artifact', 0)} evidence={s.get('evidence', 0)} "
                  f"relationships={s['relationships']}")
    for k in ("pass", "fail", "unknown", "not_applicable"):
        if s.get(f"evidence_{k}"):
            colour = {"pass": "green", "fail": "red"}.get(k, "yellow")
            console.print(f"  [{colour}]{k}[/]: {s[f'evidence_{k}']}")


# ---------------------------------------------------------------- vendor --
vendor_app = typer.Typer(help="Vendored upstreams: provenance, drift and contracts.")
app.add_typer(vendor_app, name="vendor")

_SEV_COLOUR = {"error": "red", "warning": "yellow", "info": "dim", "none": "green"}


@vendor_app.command("list")
def cmd_vendor_list(verbose: bool = typer.Option(False, "--verbose", "-v",
                                                 help="show every adopted path")) -> None:
    """Every upstream, what it gave us, and whether we are on the reviewed commit."""
    from pf.vendor.model import drift, load_registry

    ups = load_registry()
    by_id = {d.upstream_id: d for d in drift(root(), ups)}
    t = Table(box=None, pad_edge=False)
    for c in ("upstream", "role", "licence", "adopted", "declined", "state"):
        t.add_column(c)
    for u in ups:
        d = by_id.get(u.id)
        if d is None or not d.current:
            state = "[red]missing[/]"
        elif not d.locked:
            state = "[yellow]never reviewed[/]"
        elif not d.moved:
            state = "[green]reviewed[/]"
        elif d.needs_review:
            state = f"[{_SEV_COLOUR[d.severity]}]drift ({len(d.paths)})[/]"
        else:
            state = "[dim]moved, nothing adopted[/]"
        lic = u.licence if not u.needs_licence_review else f"[yellow]{u.licence} ![/]"
        t.add_row(u.id, u.role, lic, str(len(u.adopted)), str(len(u.declined)), state)
    console.print(t)
    flagged = [u for u in ups if u.needs_licence_review]
    if flagged:
        console.print(f"\n[yellow]![/] licence review outstanding: "
                      + ", ".join(u.id for u in flagged)
                      + "  →  `pf vendor licences`")
    if verbose:
        for u in ups:
            console.print(f"\n[bold]{u.id}[/] {u.url}")
            for a in u.adopted:
                colour = _SEV_COLOUR[a.severity]
                console.print(f"  [{colour}]{a.kind:<7}[/] {a.upstream}")
                for o in a.ours:
                    console.print(f"          [dim]→ {o}[/]")


@vendor_app.command("licences")
def cmd_vendor_licences() -> None:
    """Licences, and the ones that constrain how this platform may be used."""
    from pf.vendor.model import load_registry

    for u in load_registry():
        console.print(f"[bold]{u.id}[/]  {u.licence}")
        if u.licence_review:
            console.print(f"  [yellow]{u.licence_review}[/]")


@vendor_app.command("why")
def cmd_vendor_why(path: str) -> None:
    """Where a file of ours came from, and what we changed."""
    from pf.vendor.model import why as vendor_why

    hits = vendor_why(root(), path)
    if not hits:
        console.print(f"[dim]{path} has no recorded upstream — it is ours.[/]")
        return
    for u, a in hits:
        console.print(f"[bold]{u.name}[/] [dim]{u.url}[/]")
        console.print(f"  {a.kind}: [cyan]{a.upstream}[/]")
        if a.note:
            console.print(f"  [dim]{' '.join(a.note.split())}[/]")


@vendor_app.command("drift")
def cmd_vendor_drift(fail: bool = typer.Option(False, "--fail",
                                               help="exit 1 when review is needed")) -> None:
    """What moved since a human last reviewed it. Local only — never fetches."""
    from pf.vendor.model import drift

    reports = drift(root())
    _render_drift(reports)
    if fail and any(d.needs_review for d in reports):
        raise typer.Exit(1)


@vendor_app.command("sync")
def cmd_vendor_sync(only: str = typer.Option("", help="one upstream id"),
                    approve: bool = typer.Option(
                        False, "--approve",
                        help="record the new state as reviewed (only when nothing "
                             "adopted changed)")) -> None:
    """Fetch each upstream's tracking branch, then report what it means for us."""
    from pf.vendor.model import approve as approve_lock, sync as vendor_sync

    reports, errors = vendor_sync(root(), only=only)
    for e in errors:
        console.print(f"[red]fetch failed[/] {e}")
    _render_drift(reports)
    clean = [d.upstream_id for d in reports if d.moved and not d.needs_review]
    if approve and clean:
        approve_lock(root(), clean)
        console.print(f"[green]✓[/] recorded as reviewed: {', '.join(clean)}")
    elif clean:
        console.print(f"[dim]fast-forwardable (nothing adopted changed): "
                      f"{', '.join(clean)} — re-run with --approve[/]")
    if any(d.needs_review for d in reports):
        console.print("[yellow]![/] review the affected files, then "
                      "`pf vendor approve <id>`")


@vendor_app.command("approve")
def cmd_vendor_approve(ids: list[str] = typer.Argument(None)) -> None:
    """Record the current checkout as the reviewed state."""
    from pf.vendor.model import approve as approve_lock

    path, done = approve_lock(root(), list(ids) if ids else None)
    console.print(f"[green]✓[/] {path}")
    console.print(f"  reviewed: {', '.join(done)}")


@vendor_app.command("docs")
def cmd_vendor_docs() -> None:
    """Regenerate docs/VENDOR.md and the token-budgeted docs/VENDOR-CARD.md."""
    from pf.kg.card import estimate_tokens
    from pf.vendor.card import VENDOR_CARD_BUDGET, render_card, render_doc

    doc = render_doc(root())
    card = render_card(root())
    n = estimate_tokens(card.read_text())
    console.print(f"[green]✓[/] {doc}  [dim]{len(doc.read_text().splitlines())} lines[/]")
    colour = "green" if n <= VENDOR_CARD_BUDGET else "red"
    console.print(f"[green]✓[/] {card}  [{colour}]~{n} / {VENDOR_CARD_BUDGET} tokens[/]")
    raise typer.Exit(1 if n > VENDOR_CARD_BUDGET else 0)


@vendor_app.command("verify")
def cmd_vendor_verify(group: str = typer.Argument(""),
                      project: str = typer.Argument("")) -> None:
    """Do the declared paths still exist, and do the schema contracts still hold?"""
    from pf.vendor.verify import verify

    target = (group, project, pdir(group, project)) if group and project else None
    if target is None:
        for g, p, d in all_projects():
            if (d / "kg" / "graph.duckdb").exists():
                target = (g, p, d)
                break
    res = verify(root(), target)
    for f in res.findings:
        console.print(f"  [{_SEV_COLOUR[f.severity]}]{f}[/]")
    n_err = len(res.errors)
    colour = "red" if n_err else "green"
    console.print(f"[{colour}]{res.checked} contract(s) checked, {n_err} error(s)[/]")
    raise typer.Exit(1 if n_err else 0)


def _render_drift(reports: list) -> None:
    any_drift = False
    for d in reports:
        if not d.current:
            console.print(f"[red]{d.upstream_id}[/] not checked out")
            continue
        if not d.locked:
            console.print(f"[yellow]{d.upstream_id}[/] never reviewed "
                          f"({d.current[:8]}) — `pf vendor approve {d.upstream_id}`")
            any_drift = True
            continue
        # Paths are rendered even when the commit matches: same commit, different
        # path OID means the lock was edited by hand or the branch was force-pushed,
        # and silently passing that would defeat the point of locking at all.
        if not d.moved and not d.paths:
            continue
        any_drift = True
        behind = f"{d.commits_behind} commit(s)" if d.commits_behind >= 0 else "shallow"
        head = (f"[{_SEV_COLOUR[d.severity]}]{d.upstream_id}[/] "
                + (f"{d.locked[:8]} → {d.current[:8]} ({behind})" if d.moved
                   else f"{d.current[:8]} [red]lock inconsistent[/]"))
        if not d.paths:
            console.print(f"{head} [dim]— nothing we adopted changed[/]")
            continue
        console.print(head)
        for p in d.paths:
            console.print(f"    [{_SEV_COLOUR[p.severity]}]{p.state:<8}[/] {p.path}")
            for o in p.ours:
                console.print(f"             [cyan]review → {o}[/]")
    if not any_drift:
        console.print("[green]every upstream is on its reviewed commit[/]")


# ---------------------------------------------------------------- report --
report_app = typer.Typer(help="Evidence BI reporting layer.")
app.add_typer(report_app, name="report")


@report_app.command("build")
def cmd_report_build(group: str, project: str) -> None:
    """Regenerate the Evidence project from the semantic layer."""
    from pf.projections.evidence import build as build_evidence

    d = pdir(group, project)
    r = build_evidence(d, group, project)
    console.print(f"[green]✓[/] {r['path']}")
    console.print(f"  {r['metrics']} metric(s) compiled · {r['pages']} page(s) · "
                  f"{r['sources']} source extract(s)")
    if r["unbacked"]:
        console.print(f"  [yellow]![/] no time dimension: {', '.join(r['unbacked'])}")
    if not r["metrics"]:
        console.print("  [yellow]![/] no metrics in the semantic layer yet — "
                      "add them in transform/models/semantic/, then `pf seed`")


@report_app.command("audit")
def cmd_report_audit(group: str, project: str) -> None:
    """Mechanical quality score for the reporting layer."""
    from pf.projections.report_audit import audit as audit_report

    score, findings = audit_report(pdir(group, project))
    for f in findings:
        colour = {"error": "red", "warning": "yellow", "info": "dim"}[f.severity]
        console.print(f"  [{colour}]{f}[/]")
    colour = "green" if score >= 90 else "yellow" if score >= 70 else "red"
    console.print(f"[{colour}]Report score: {score}/100[/] "
                  f"({sum(1 for f in findings if f.severity == 'error')} error(s), "
                  f"{sum(1 for f in findings if f.severity == 'warning')} warning(s))")
    raise typer.Exit(1 if any(f.severity == "error" for f in findings) else 0)


@report_app.command("dev")
def cmd_report_dev(group: str, project: str) -> None:
    """Run the Evidence dev server for this project."""
    d = pdir(group, project) / "reporting"
    if not (d / "node_modules").exists():
        console.print("[yellow]installing dependencies (first run)…[/]")
        subprocess.run(["npm", "install"], cwd=str(d), check=False)
    console.print(f"[green]→[/] http://localhost:3000")
    subprocess.run(["npm", "run", "dev"], cwd=str(d), check=False)


# -------------------------------------------------------------------- pr --
pr_app = typer.Typer(help="Per-pull-request platform impact report.")
app.add_typer(pr_app, name="pr")


@pr_app.command("report")
def cmd_pr_report(number: int = typer.Option(0, help="PR number (defaults to $GITHUB_REF)"),
                  base: str = typer.Option("", help="base ref to diff against"),
                  title: str = typer.Option(""),
                  markdown_out: str = typer.Option("", "--markdown",
                                                   help="also write the comment body here"),
                  fail: bool = typer.Option(False, "--fail",
                                            help="exit 1 when the verdict is `block`")) -> None:
    """Blast radius, conformance, readiness and vendor drift for this change."""
    from pf.pr import build as build_pr, markdown as pr_markdown, pr_number_from_env, save

    r = build_pr(root(), number or pr_number_from_env(), base, title)
    body = pr_markdown(r)
    path = save(root(), r)
    if markdown_out:
        Path(markdown_out).write_text(body + "\n")
    console.print(body)
    console.print(f"\n[dim]{path}[/]")
    if fail and r.verdict == "block":
        raise typer.Exit(1)


@pr_app.command("list")
def cmd_pr_list() -> None:
    """Reports recorded so far — what the UI's PR view shows."""
    from pf.pr import load_all

    rows = load_all(root())
    if not rows:
        console.print("[dim]no reports yet — run `pf pr report`[/]")
        return
    t = Table(box=None, pad_edge=False)
    for c in ("pr", "verdict", "branch", "projects", "files", "generated"):
        t.add_column(c)
    for r in rows:
        colour = {"block": "red", "review": "yellow", "clear": "green"}[r["verdict"]]
        t.add_row(str(r["number"] or "-"), f"[{colour}]{r['verdict']}[/]", r["branch"],
                  ", ".join(f"{p['group']}/{p['project']}" for p in r["projects"]) or "-",
                  str(len(r["files"])), r["generated_at"][:19])
    console.print(t)


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
