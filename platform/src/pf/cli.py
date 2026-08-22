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
    CAPABILITIES,
    UnknownCapability,
    gate_additions,
    missing_env,
)
from pf.capabilities import (
    apply as apply_capability,
)
from pf.capabilities import (
    defaults as capability_defaults,
)
from pf.capabilities import (
    resolve as resolve_capabilities,
)
from pf.kg.build import build_graph
from pf.kg.card import GROUP_CARD_BUDGET, PROJECT_CARD_BUDGET, estimate_tokens, render_group_card, render_project_card

# Aliased: the `gate` command below is a *path* gate and would otherwise shadow
# this import at module level, so `pf impact-gate` would call the wrong one.
from pf.kg.impact import (
    GateNotExercised,
    impact_of,
    impact_of_many,
)
from pf.kg.impact import (
    gate as impact_gate,
)
from pf.kg.query import kg_neighbors, kg_search
from pf.loops.audit import audit as loop_audit
from pf.loops.audit import project_readiness, recommended_level
from pf.loops.gate import GateResult, check_paths, nodes_for, project_for, tracked_denied
from pf.loops.registry import BODIES, SPECS
from pf.loops.runner import Ledger, run_loop, update_state
from pf.ontology.model import load_ontology
from pf.ontology.validate import validate_instance, validate_project, validate_topology
from pf.runtime.staging import generate as generate_staging
from pf.scaffold.bootstrap import STEPS, bootstrap
from pf.scaffold.generator import new_group, new_project
from pf.stack import frontdoor, storage, token

app = typer.Typer(add_completion=False, help="Agentic data platform control CLI.")
kg_app = typer.Typer(help="Knowledge graph operations.")
app.add_typer(kg_app, name="kg")
console = Console()

# A tool's scaffold-time half *is* a capability, so it is merged into the same
# registry `pf new-project --with` and `pf capability-add` read. One scaffolder,
# one gate merge — a tool is not a second way to write files into a project.
# Done here rather than in pf.capabilities to keep that module free of any
# dependency on the tool layer.
from pf.tools import register_capabilities as _register_tool_capabilities  # noqa: E402

_register_tool_capabilities()


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
    with_: str = typer.Option("", "--with", help="comma-separated capabilities to add "
                                                 "on top of the defaults "
                                                 "(see `pf capabilities`)"),
    without: str = typer.Option("", "--without", help="comma-separated default "
                                                      "capabilities to skip"),
) -> None:
    """Create a project (one legal entity) inside a group.

    One command, everything wired: scaffold, knowledge graph, group card,
    optional capabilities, gate rules, and the Dagster code location. Nothing
    here is a follow-up step you can forget — a half-registered project is how a
    gate ends up inert.
    """
    sister_list = [s.strip() for s in sisters.split(",") if s.strip()]
    # Defaults first, `--with` on top, `--without` removed. A project that has to
    # be asked for its capabilities gets the ones whoever typed the command
    # remembered — which is how seven projects ended up with no CI merge gate
    # while the eighth had one. Opting out stays possible and stays explicit.
    skip = {c.strip() for c in without.split(",") if c.strip()}
    names = [n for n in capability_defaults() if n not in skip]
    names += [c.strip() for c in with_.split(",")
              if c.strip() and c.strip() not in names]
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


_SEVERITY_STYLE = {"blocks": "red", "decide": "yellow", "note": "dim"}


def _print_risks(risks: list) -> None:
    for r in risks:
        style = _SEVERITY_STYLE.get(r.severity, "white")
        console.print(f"  [{style}]{r.severity:>6}[/] [bold]{r.kind}[/]  {r.detail}")
        console.print(f"         [dim]{r.remedy}[/]")


@app.command("onboard")
def cmd_onboard(
    group: str, project: str, source: str,
    apply_: bool = typer.Option(False, "--apply", help="write the changes; default is a plan"),
    force: bool = typer.Option(False, "--force", help="apply despite blocking findings"),
) -> None:
    """Adopt an existing repository (git URL or path) as a project.

    Plans by default. The apply writes a whole project, rewrites an orchestrator
    and merges dependency files — the moment to find out where `intermediate/`
    landed is before it happens.
    """
    from pf.onboard import apply as apply_plan
    from pf.onboard import plan as make_plan
    from pf.onboard import resolve_source

    scratch = root() / "data" / "onboard" / f"{group}-{project}"
    try:
        src = resolve_source(source, scratch)
    except RuntimeError as exc:
        console.print(f"[red]✗[/] {exc}")
        raise typer.Exit(1) from exc

    p = make_plan(root(), group, project, src)
    s = p.survey

    console.print(f"[bold]{src}[/] [dim]→ {group}/{project}[/]")
    console.print(f"  dbt: [cyan]{s.dbt_name or 'none found'}[/] "
                  f"({s.sql_model_count} model(s), {len(s.macros)} macro(s), "
                  f"{len(s.seeds)} seed(s), {len(s.tests)} test(s))")
    if s.layer_mapping:
        console.print("  layers: " + ", ".join(
            f"{k}→{v}" for k, v in sorted(s.layer_mapping.items())))
    if s.orchestrators:
        console.print(f"  orchestrator: [cyan]{', '.join(sorted(s.orchestrators))}[/]")
    if s.ingestion:
        console.print(f"  ingestion: {', '.join(sorted(s.ingestion))}")
    if s.warehouses:
        console.print(f"  warehouse: {', '.join(sorted(s.warehouses))}")

    console.print("\n[bold]plan[/]")
    for a in p.actions:
        count = f" [dim]×{a.count}[/]" if a.count else ""
        console.print(f"  [green]+[/] {a.kind:<12} {a.detail}{count}")

    if p.risks:
        console.print("\n[bold]findings[/]")
        _print_risks(p.risks)
    for w in p.warnings:
        console.print(f"  [yellow]![/] {w}")

    if not apply_:
        console.print("\n[dim]plan only — re-run with --apply to write it[/]")
        raise typer.Exit(0)

    # A blocking finding means the result either will not build or will build
    # and be wrong. Applying over the top of that produces a project someone
    # then has to un-import, so it takes a deliberate second instruction.
    if p.blocking and not force:
        console.print(f"\n[red]✗[/] {len(p.blocking)} blocking finding(s) — "
                      f"resolve them, or re-run with --force to apply anyway")
        raise typer.Exit(1)

    console.print("\n[bold]applying[/]")
    try:
        for line in apply_plan(root(), p):
            console.print(f"  [green]✓[/] {line}")
    except FileExistsError as exc:
        console.print(f"  [red]✗[/] {exc}")
        raise typer.Exit(1) from exc

    _print_bootstrap(bootstrap(root(), group, project))

    console.print("\n[bold]still to do[/] [dim]— the part no tool can infer[/]")
    for item in p.checklist:
        console.print(f"  [yellow]□[/] {item}")


@app.command("dialect")
def cmd_dialect(
    path: str = typer.Argument(".", help="a repo, a project, or any directory of SQL"),
) -> None:
    """Which SQL functions a tree calls, and whether they are portable.

    Not only for imports. Run it against an existing project after adopting SQL
    from anywhere. The ambiguous findings deserve the attention: those already
    run, and can already be wrong.
    """
    from pf.onboard.dialect import AMBIGUOUS, UNSUPPORTED, analyse, toolkit_macros
    from pf.onboard.survey import is_build_artifact

    target = Path(path).expanduser().resolve()
    files = [f for f in target.rglob("*.sql")
             if not is_build_artifact(f.relative_to(target).parts)]
    if not files:
        console.print(f"[yellow]![/] no .sql under {target}")
        raise typer.Exit(0)

    local = {f.stem for f in files if "macros" in f.parts}
    r = analyse(files, local_macros=local)
    console.print(f"[bold]{target}[/] [dim]— {len(files)} file(s), "
                  f"{len(r.calls)} distinct function(s)[/]")

    if r.clean:
        console.print("\n[green]✓[/] every call is portable as written")
        return

    available = toolkit_macros(root())

    if r.ambiguous:
        console.print("\n[red]ambiguous[/] [dim]— these run, and can be wrong[/]")
        for name, n in r.ambiguous.most_common():
            console.print(f"  [yellow]![/] [bold]{name}[/] [dim]×{n}[/] — {AMBIGUOUS[name]}")
    if r.covered:
        console.print("\n[yellow]needs wrapping[/] [dim]— a portable macro exists[/]")
        for name, n in r.covered.most_common():
            macro = UNSUPPORTED[name].macro
            missing = "" if macro in available else " [red](macro not found!)[/]"
            console.print(f"  [yellow]→[/] {name} [dim]×{n}[/]  "
                          f"use [cyan]{{{{ {macro}(...) }}}}[/]"
                          f" [dim]({UNSUPPORTED[name].seen_in})[/]{missing}")
    if r.unsupported:
        console.print("\n[red]unsupported[/] [dim]— no macro covers these[/]")
        for name, n in r.unsupported.most_common():
            console.print(f"  [red]✗[/] {name} [dim]×{n}[/]")

    console.print(f"\n[dim]{len(available)} portable macro(s) available from "
                  f"platform/toolkits/[/]")


# ------------------------------------------------------------- the ladder --
align_app = typer.Typer(help="Onboarding ladder: evaluate → implement → validate, "
                             "one stage at a time.")
app.add_typer(align_app, name="align")

_MARK = {"pass": ("green", "✓"), "fail": ("red", "✗"), "unexercised": ("yellow", "?")}


def _print_verdict(stage, verdict) -> None:
    for c in verdict.checks:
        style, glyph = _MARK[c.status]
        console.print(f"    [{style}]{glyph}[/] {c.name:<34} [dim]{c.evidence}[/]")


@align_app.command("status")
def cmd_align_status(
    group: str, project: str,
    write_state: bool = typer.Option(False, "--state",
                                     help="also write the position into STATE.md"),
) -> None:
    """Which rung of the onboarding ladder this project is on.

    Every verdict is re-derived from the project on disk, so it cannot be stale.
    The ladder stops at the first closed gate rather than reporting the stages
    behind it, whose findings a fix upstream would erase anyway.

    `--state` writes the position to STATE.md, the durable spine that outlives a
    conversation. The verdicts are still not stored — only where the ladder
    stopped and what it stopped on, both re-derived on every write.
    """
    from pf.onboard.ladder import STAGES, ladder, state_entries

    rungs = ladder(root(), group, project)
    console.print(f"[bold]{group}/{project}[/] [dim]— onboarding ladder[/]\n")

    done = 0
    for stage, verdict in rungs:
        if verdict.complete:
            console.print(f"  [green]✓[/] [bold]{stage.name}[/] [dim]{verdict.summary}[/]")
            done += 1
        elif verdict.open:
            console.print(f"  [yellow]~[/] [bold]{stage.name}[/] [dim]{verdict.summary}[/]")
            _print_verdict(stage, verdict)
            done += 1
        else:
            console.print(f"  [red]✗[/] [bold]{stage.name}[/] — {stage.subject}")
            _print_verdict(stage, verdict)

    remaining = [s.name for s in STAGES[len(rungs):]]
    if remaining:
        console.print(f"  [dim]· {', '.join(remaining)} — not reached[/]")
    console.print(f"\n[dim]{done}/{len(STAGES)} stage(s) open. "
                  f"`pf align evaluate {group} {project}` for what to do next.[/]")

    if write_state:
        from pf.loops.runner import update_state

        p = update_state(root(), state_entries(root(), group, project))
        console.print(f"[dim]wrote {p.relative_to(root())}[/]")

    raise typer.Exit(0 if done == len(STAGES) else 1)


@align_app.command("evaluate")
def cmd_align_evaluate(
    group: str, project: str,
    stage: str = typer.Option("", "--stage", help="a stage name; default is the current one"),
) -> None:
    """Phase one of a stage: what is wrong, and what to do about it.

    Read-only and free. Nothing here calls a model — the findings are derived
    from the project, and the judgement they need is the implement phase's job.
    """
    from pf.onboard.ladder import BY_NAME, Ctx, current

    if stage:
        if stage not in BY_NAME:
            console.print(f"[red]unknown stage '{stage}'[/] — "
                          f"{', '.join(BY_NAME)}")
            raise typer.Exit(1)
        st = BY_NAME[stage]
    else:
        cur = current(root(), group, project)
        if cur is None:
            console.print(f"[green]✓[/] {group}/{project} is through every stage")
            raise typer.Exit(0)
        st = cur[0]

    c = Ctx(root=root(), group=group, project=project)
    risks = st.evaluate(c)
    console.print(f"[bold]{group}/{project}[/] [dim]— stage[/] [cyan]{st.name}[/]")
    console.print(f"[dim]{st.subject}[/]\n")
    if not risks:
        console.print("[green]✓[/] nothing to do — run "
                      f"[cyan]pf align validate {group} {project} --stage {st.name}[/]")
        raise typer.Exit(0)
    _print_risks(risks)
    console.print(f"\n[dim]implement: read {st.reference} in the project-onboarding "
                  f"toolkit, fix one finding, then validate.[/]")
    raise typer.Exit(1 if any(r.blocking for r in risks) else 0)


@align_app.command("validate")
def cmd_align_validate(
    group: str, project: str,
    stage: str = typer.Option("", "--stage", help="a stage name; default is the current one"),
) -> None:
    """Phase three of a stage: the gate, with the evidence for its verdict.

    A check reports `unexercised` when the tool that would decide it is not
    installed. That is not a pass — it is the honest answer, and it does not
    close the gate, because a missing MetricFlow CLI must not wall a project off
    from the rest of the ladder.
    """
    from pf.onboard.ladder import BY_NAME, Ctx, Verdict, current, record

    if stage and stage not in BY_NAME:
        console.print(f"[red]unknown stage '{stage}'[/] — {', '.join(BY_NAME)}")
        raise typer.Exit(1)
    if stage:
        st = BY_NAME[stage]
    else:
        cur = current(root(), group, project)
        if cur is None:
            console.print(f"[green]✓[/] {group}/{project} is through every stage")
            raise typer.Exit(0)
        st = cur[0]

    c = Ctx(root=root(), group=group, project=project)
    verdict = Verdict(st.name, st.validate(c))
    console.print(f"[bold]{group}/{project}[/] [dim]— stage[/] [cyan]{st.name}[/]\n")
    _print_verdict(st, verdict)

    allowed, why = record(root(), group, project, st, verdict)

    if verdict.complete:
        console.print(f"\n[green]✓[/] {verdict.summary} — the next stage is open")
        raise typer.Exit(0)
    if verdict.open:
        console.print(f"\n[yellow]~[/] {verdict.summary}. The gate is open; the "
                      f"unexercised checks are gaps in the evidence, not passes.")
        raise typer.Exit(0)

    console.print(f"\n[red]✗[/] {verdict.summary} — "
                  f"`pf align evaluate {group} {project} --stage {st.name}`")
    if not allowed:
        console.print(f"\n[red]■ {why}[/]")
        console.print("[dim]Stop. Do not attempt this stage a fourth time — "
                      "report what was tried and what decision it needs. "
                      f"`pf loop reset onboard-{st.name} {group} {project}` "
                      "clears the breaker once that decision is made.[/]")
    raise typer.Exit(1)


@align_app.command("verify")
def cmd_align_verify(
    group: str, project: str,
    stage: str = typer.Option("", "--stage", help="a stage name; default is the current one"),
) -> None:
    """The checker half: judge the change, not the result.

    `validate` asks whether the project is correct now. This asks whether the
    change that got it there is one to accept — scope, size, and whether
    anything was switched off rather than fixed. They catch different things: a
    project passes every gate if you delete the test that was failing.

    Run it before committing a stage's work, and treat a rejection as a
    rejection. The default stance of a checker is no.
    """
    from pf.onboard.ladder import BY_NAME, Ctx, Verdict, current, verify

    if stage and stage not in BY_NAME:
        console.print(f"[red]unknown stage '{stage}'[/] — {', '.join(BY_NAME)}")
        raise typer.Exit(1)
    if stage:
        st = BY_NAME[stage]
    else:
        cur = current(root(), group, project)
        if cur is None:
            console.print(f"[green]✓[/] {group}/{project} is through every stage")
            raise typer.Exit(0)
        st = cur[0]

    c = Ctx(root=root(), group=group, project=project)
    verdict = Verdict(st.name, verify(c, st))
    console.print(f"[bold]{group}/{project}[/] [dim]— checker on stage[/] "
                  f"[cyan]{st.name}[/]\n")
    _print_verdict(st, verdict)
    if verdict.failures:
        console.print(f"\n[red]✗ REJECT[/] — {verdict.summary}. Narrow the change "
                      f"to what the finding needed and re-run.")
        raise typer.Exit(1)
    console.print(f"\n[green]✓ ACCEPT[/] — {verdict.summary}. Scope and shape are "
                  f"fine; whether it addresses the right finding is not decidable "
                  f"here and is still yours to confirm.")
    raise typer.Exit(0)


@align_app.command("stages")
def cmd_align_stages() -> None:
    """The ladder itself: what each stage is for, and why it is where it is."""
    from pf.onboard.ladder import STAGES

    table = Table()
    table.add_column("#", justify="right", style="dim")
    table.add_column("stage", style="cyan")
    table.add_column("subject")
    table.add_column("budget", justify="right", style="dim")
    for i, s in enumerate(STAGES, 1):
        table.add_row(str(i), s.name, s.subject,
                      f"{s.token_budget:,}" if s.token_budget else "0")
    console.print(table)
    console.print("[dim]Each stage is evaluate → implement → validate. The gate "
                  "is code; only the middle phase is an agent's.[/]")


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
def cmd_kg_build(group: str = typer.Argument("", help="omit for every group"),
                 project: str = typer.Argument("", help="omit for every project in the group"),
                 parse: bool = typer.Option(
                     True, help="parse the dbt project first if it has no manifest")) -> None:
    """Rebuild knowledge graphs. No arguments → every project."""
    targets = _targets(group, project)
    rows: list[tuple[str, dict[str, int]]] = []
    for g, p, d in targets:
        # The builder treats the manifest as optional and degrades without it.
        # That is the right default for a source of documentation and the wrong
        # one for the graph CI gates against: no manifest means no Model, Metric
        # or Exposure nodes, and a blast-radius query over that graph finds
        # nothing and says so.
        if parse:
            from pf.runtime.dbt_runtime import ensure_manifest
            from pf.runtime.warehouse import Warehouse
            ensure_manifest(d, duckdb_path=Warehouse.for_project(d, g, p).path)
        rows.append((f"{g}/{p}", build_graph(d, group=g, project=p)))

    if len(rows) == 1:
        name, counts = rows[0]
        t = Table("kind", "nodes", title=f"{name} graph")
        for k, v in sorted(counts.items()):
            t.add_row(k, str(v))
        console.print(t)
        return

    # Across many projects the per-kind breakdown is noise; what is worth seeing
    # at a glance is the kinds whose absence means something. A zero here is the
    # finding — no Model means the gate cannot run at all.
    t = Table("project", "nodes", "models", "metrics", "policies",
              title=f"{len(rows)} graph(s) rebuilt")
    for name, counts in rows:
        def cell(kind: str, c: dict[str, int] = counts) -> str:
            n = c.get(kind, 0)
            return str(n) if n else "[red]0[/]"
        t.add_row(name, str(sum(counts.values())),
                  cell("Model"), cell("Metric"), cell("Policy"))
    console.print(t)


@kg_app.command("card")
def cmd_kg_card(group: str = typer.Argument("", help="omit for every group"),
                project: str = typer.Argument("", help="omit for every project in the group")) -> None:
    """Regenerate context cards. No arguments → every project."""
    targets = _targets(group, project)
    for g, p, d in targets:
        card = render_project_card(d, g, p)
        tokens = estimate_tokens(card.read_text())
        ok = tokens <= PROJECT_CARD_BUDGET
        # Rendering reports the budget but does not enforce it — `pf tokens` is
        # the enforcement point, and having two commands fail on the same
        # condition means fixing it twice and trusting neither.
        console.print(f"[{'green' if ok else 'red'}]✓[/] {g}/{p}"
                      f"  [dim](~{tokens} tokens / {PROJECT_CARD_BUDGET})[/]")
    # Once per group, not once per project: the group card is a roster of
    # sisters, so rendering it inside the loop rewrites the same file N times.
    for g in sorted({g for g, _, _ in targets}):
        render_group_card(root() / "groups" / g, g)


@kg_app.command("check")
def cmd_kg_check(group: str = typer.Argument("", help="omit for every group"),
                 project: str = typer.Argument("", help="omit for every project in the group"),
                 strict: bool = typer.Option(
                     False, "--strict",
                     help="a project that cannot be judged fails too"),
                 parse: bool = typer.Option(
                     True, help="parse the dbt project first if it has no manifest")) -> None:
    """Is each committed graph current with the dbt project beside it?

    The graph has no clock. One built before a model landed answers every query
    confidently and wrongly, and nothing else in the repo notices — it simply
    holds fewer nodes than the project has models. This is what notices.
    """
    from pf.kg.build import graph_drift

    drifted = unexercised = 0
    for g, p, d in _targets(group, project):
        # `target/` is gitignored, so a fresh checkout — every CI runner — has no
        # manifest to compare the committed graph against. Without this the check
        # reports "not exercised" everywhere it matters most and passes.
        if parse:
            from pf.runtime.dbt_runtime import ensure_manifest
            from pf.runtime.warehouse import Warehouse
            try:
                ensure_manifest(d, duckdb_path=Warehouse.for_project(d, g, p).path)
            except Exception as exc:  # noqa: BLE001 — reported per project, not fatal
                console.print(f"[dim]{g}/{p}: dbt parse failed — {exc}[/]")
        report = graph_drift(d, f"{g}/{p}")
        console.print(report.render())
        if not report.exercised:
            unexercised += 1
        elif report.total:
            drifted += 1

    if drifted:
        console.print(f"[red]{drifted} stale graph(s)[/] — run `pf kg build` and commit "
                      f"kg/graph.json")
    if unexercised and strict:
        console.print(f"[red]{unexercised} graph(s) could not be checked[/]")
    raise typer.Exit(1 if drifted or (unexercised and strict) else 0)


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
    try:
        code, rendered = impact_gate(gp, [n.strip() for n in nodes.split(",") if n.strip()])
    except GateNotExercised as exc:
        console.print(f"[red]✗[/] gate not exercised — {exc}")
        raise typer.Exit(1) from exc
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

    topo = validate_topology()
    topo_errors = [i for i in topo if i.severity == "error"]
    mark = "[red]✗[/]" if topo_errors else "[green]✓[/]"
    console.print(f"{mark} ontology + topology  {len(topo_errors)} error(s), "
                  f"{len(topo) - len(topo_errors)} warning(s)")
    for i in topo:
        console.print(f"    {i}")

    failed = bool(topo_errors) or bool(tracked)
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


@app.command("evals-gen")
def cmd_evals_gen(group: str, project: str,
                  toolkit: str = typer.Option("", help="only templates from these toolkits (comma-separated)"),
                  ) -> None:
    """Ground every toolkit's eval templates in this project's own models.

    A toolkit knows what correct judgement looks like; it cannot know which
    tables to say it about. This resolves the second half from the project's
    knowledge graph and writes real cases into `evals/cases/generated/`.
    """
    from pf.evals.generate import generate
    from pf.evals.template import TemplateError

    pdir(group, project)  # exits if the project does not exist
    wanted = {t.strip() for t in toolkit.split(",") if t.strip()} or None

    try:
        results = generate(root(), group, project, toolkits=wanted)
    except TemplateError as exc:
        console.print(f"[red]✗[/] {exc}")
        raise typer.Exit(1) from exc

    if not results:
        console.print("[yellow]no templates found[/] [dim]— toolkits ship them in "
                      "platform/toolkits/<toolkit>/evals/templates/[/]")
        raise typer.Exit(0)

    for r in results:
        if r.path:
            console.print(f"  [green]✓[/] {r.template.toolkit:<14} {r.template.name}")
        else:
            console.print(f"  [yellow]–[/] {r.template.toolkit:<14} {r.template.name} "
                          f"[dim]{r.skipped}[/]")

    written = [r for r in results if r.path]
    console.print(f"\n{len(written)} case(s) written to "
                  f"groups/{group}/projects/{project}/evals/cases/generated/")
    if written:
        console.print("[dim]Generated from this project's models — the reasoning is the "
                      "toolkit's, the expectations are a starting point. Read them "
                      "before trusting a green run.[/]")


@app.command()
def evals(group: str = typer.Argument("", help="omit to run the platform tier alone"),
          project: str = typer.Argument(""),
          live: bool = typer.Option(False, "--live",
                                    help="call the real models and grade the responses (costs money)"),
          samples: int = typer.Option(1, help="samples per live case; >1 exposes unstable prompts"),
          agent: str = typer.Option("", help="only cases for this agent"),
          tag: str = typer.Option("", help="only cases carrying this tag"),
          scope: str = typer.Option("", help="platform, group or project; default is every tier that applies"),
          ) -> None:
    """Test the parts of this platform that are prompts.

    Two tiers. The contract tier is deterministic, needs no credential and costs
    nothing, so it runs by default and belongs in CI. The live tier calls the
    real models and is the only one that can tell you a prompt got worse — it is
    opt-in because it bills.
    """
    from pf.evals import discover, run_contract, run_live
    from pf.evals.case import CaseError

    scopes = {s.strip() for s in scope.split(",") if s.strip()} or None

    # --------------------------------------------------------- contract ----
    console.print("[bold]contract[/] [dim]— no credential, no spend[/]")
    contract = run_contract(root(), group, project)
    for r in contract:
        mark = {"pass": "[green]✓[/]", "warn": "[yellow]![/]", "fail": "[red]✗[/]"}[r.outcome]
        console.print(f"  {mark} {r.name:<44} [dim]{r.detail}[/]")
    failed = any(r.outcome == "fail" for r in contract)

    # ------------------------------------------------------------ cases ----
    # Loading every case is itself a check: a malformed fixture or an expectation
    # naming a field the schema does not have is caught here, for free, instead
    # of after a round of billed calls.
    try:
        cases = discover(root(), group or None, project or None,
                         agents={agent} if agent else None,
                         tags={tag} if tag else None,
                         scopes=scopes)
    except CaseError as exc:
        console.print(f"[red]✗[/] {exc}")
        raise typer.Exit(1) from exc

    tiers: dict[str, list] = {}
    for c in cases:
        tiers.setdefault(c.scope, []).append(c)

    console.print(f"\n[bold]cases[/] [dim]— {len(cases)} loaded[/]")
    for tier in ("platform", "group", "project"):
        owned: dict[str, int] = {}
        for c in tiers.get(tier, []):
            owned[c.owner or "—"] = owned.get(c.owner or "—", 0) + 1
        if owned:
            detail = ", ".join(f"{k} ({v})" for k, v in sorted(owned.items()))
            console.print(f"  [cyan]{tier:<9}[/] {detail}")
    if not cases:
        console.print("  [dim]none — add cases to a toolkit's evals/, or this "
                      "project's evals/cases/[/]")

    if not live:
        if cases:
            console.print("\n[dim]cases loaded and valid; --live to grade them "
                          "against the real models[/]")
        raise typer.Exit(1 if failed else 0)

    # ---------------------------------------------------------- live -------
    if not group or not project:
        console.print("[red]✗[/] --live needs a group and a project: the agents "
                      "run against a project's context card")
        raise typer.Exit(1)

    from pf.agents.base import NoCredentials

    console.print(f"\n[bold]live[/] [dim]— {len(cases)} case(s) × {samples} sample(s)[/]")
    try:
        report = run_live(root(), group, project, cases, samples=samples)
    except NoCredentials as exc:
        console.print(f"[red]✗[/] {exc}")
        raise typer.Exit(1) from exc

    for r in report.results:
        if r.error:
            mark, note = "[red]✗[/]", f"[red]{r.error}[/]"
        elif r.ok:
            mark, note = "[green]✓[/]", f"[dim]{r.pass_rate}  {r.tokens:,}t[/]"
        elif r.flaky:
            mark, note = "[yellow]![/]", f"[yellow]unstable {r.pass_rate}[/]"
        else:
            mark, note = "[red]✗[/]", f"[red]{r.pass_rate}[/]"
        console.print(f"  {mark} [dim]{r.case.scope[:4]}[/] {r.case.qualified_name:<52} {note}")
        for f in r.failures:
            console.print(f"      [red]{f}[/]")

    console.print(f"\n  {report.tokens:,} tokens  ${report.usd:.4f}")
    if report.flaky:
        console.print(f"  [yellow]{len(report.flaky)} unstable[/] [dim]— passed some "
                      f"samples and not others; the prompt is not wrong, it is "
                      f"underdetermined[/]")
    raise typer.Exit(1 if failed or not report.ok else 0)


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
    for g, p, _d in sisters:
        console.print(f"[cyan]▸[/] launching {g}/{p}")
        procs.append((p, subprocess.Popen(
            [sys.executable, "-m", "pf.cli", "seed", g, p], cwd=str(root()))))
    failed = False
    for name, proc in procs:
        rc = proc.wait()
        console.print(f"  {'[green]✓[/]' if rc == 0 else '[red]✗[/]'} {name}")
        failed = failed or rc != 0
    for g, p, _d in rollups:
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


# ------------------------------------------------------------------ stack --
stack_app = typer.Typer(
    help="The control plane: one Postgres, one origin, one image.")
app.add_typer(stack_app, name="stack")


def _stack_dir() -> Path:
    return root() / "platform" / "stack"


@stack_app.command("render")
def cmd_stack_render(
    listen: int = typer.Option(frontdoor.LISTEN, help="Front-door port."),
    static: str = typer.Option("", help="Path nginx serves /pf/ from. Defaults "
                                       "to the generated www/ in this repo."),
) -> None:
    """Generate nginx, supervisor and the Dagster storage block.

    Everything here is derived from the project roster, so it is regenerated
    rather than edited: adding a sister shifts recce's port assignments, and a
    hand-edited nginx.conf would keep pointing at the old ones.
    """
    r = root()
    out = _stack_dir()
    (out / "www").mkdir(parents=True, exist_ok=True)

    roster = all_projects()
    svcs = frontdoor.services(roster)
    locs = frontdoor.code_locations(roster)
    www = static or str(out / "www")

    files = {
        out / "nginx.conf": frontdoor.nginx_conf(svcs, listen=listen, static=www),
        out / "supervisord.conf": frontdoor.supervisor_conf(
            svcs, locs, repo=r, nginx_conf_path=str(out / "nginx.conf")),
        out / "workspace.yaml": frontdoor.workspace_yaml(locs),
        out / "www" / "index.html": frontdoor.landing_html(svcs, listen=listen),
        out / "www" / "recce-down.html": frontdoor.recce_down_html(),
        out / "www" / "bar.css": frontdoor.bar_css(),
        out / "www" / "bar.js": frontdoor.bar_js(),
    }
    for path, text in files.items():
        path.write_text(text)
        console.print(f"[green]✓[/] {path.relative_to(r)}")

    s = storage.settings()
    # DAGSTER_HOME wins: the container sets it, and writing the storage block
    # into a `.dagster` the instance is not reading is a silent no-op that looks
    # exactly like success.
    home = Path(os.environ.get("DAGSTER_HOME") or (r / ".dagster"))
    path, changed = storage.write(home, s, base=r / ".dagster" / "dagster.yaml")
    where = (f"postgres {s.host}:{s.port}/{s.db} schema={s.schema}" if s
             else f"sqlite (set {storage.ENV_HOST} for postgres)")
    shown = path.relative_to(r) if path.is_relative_to(r) else path
    console.print(f"[green]✓[/] {shown}  "
                  f"{'updated' if changed else 'unchanged'} — {where}")

    ports = {x.project: x.port for x in locs}
    t = Table("project", "group", "code server", "recce", "on boot",
              title=f"{len(locs)} code location(s), {len(svcs)} review server(s)")
    for x in svcs:
        t.add_row(x.project, x.group, str(ports.get(x.project, "—")),
                  str(x.port),
                  "recce" if x.reviewed else "[dim]code only[/]")
    if svcs:
        console.print(t)


@stack_app.command("db-init")
def cmd_stack_db_init() -> None:
    """Create Dagster's role and schema in OpenMetadata's database.

    Run once, as an admin. Dagster's own role cannot do this and should not be
    able to — it has no rights in `public`, which is the entire point of putting
    the two products in one database.
    """
    s = storage.settings()
    if s is None:
        console.print(f"[red]{storage.ENV_HOST} is not set[/] — nothing to "
                      "initialise. See docs/STACK.md.")
        raise typer.Exit(1)
    admin = storage.admin_settings(s)
    try:
        for line in storage.ensure_schema(s, admin):
            console.print(f"[green]✓[/] {line}")
    except ImportError:
        console.print("[red]psycopg2 is not installed[/] — "
                      "[cyan]uv sync --extra stack[/]")
        raise typer.Exit(1) from None
    except Exception as exc:  # noqa: BLE001 - the driver raises many types
        console.print(f"[red]✗[/] {type(exc).__name__}: {exc}")
        raise typer.Exit(1) from None


@stack_app.command("token")
def cmd_stack_token() -> None:
    """Print the catalogue's ingestion-bot JWT, for `export`.

    Prints a credential to stdout — that is the whole job:

        export OPENMETADATA_JWT_TOKEN="$(pf stack token)"

    Echoes `OPENMETADATA_JWT_TOKEN` when it is already set, so the command is
    safe to use unconditionally and never overrides a deliberate choice.
    """
    s = storage.settings()
    admin = storage.admin_settings(s) if s else None
    try:
        value, _ = token.resolve(dict(os.environ), admin)
    except token.TokenUnavailable as exc:
        console.print(f"[red]✗[/] {exc}")
        raise typer.Exit(1) from None
    # print, not console.print: rich wraps at the terminal width, and a JWT
    # folded across three lines is a JWT that fails to authenticate.
    print(value)


@stack_app.command("status")
def cmd_stack_status() -> None:
    """What the stack is configured to be, and what is actually answering."""
    import urllib.error
    import urllib.request

    r = root()
    s = storage.settings()
    console.print(f"[bold]storage[/]  "
                  f"{'postgres ' + s.host + ':' + str(s.port) + '/' + s.db if s else 'sqlite (local files)'}")
    if s is None:
        # This shell's configuration, not the container's. Saying so matters:
        # the stack can be serving happily off Postgres while the host that
        # asked reads "sqlite", and that is not a disagreement.
        console.print(f"  [dim]this shell only — the stack sets "
                      f"{storage.ENV_HOST} for itself. Set it here too to "
                      f"point host-side `dagster dev` at the same database.[/]")
    if s:
        try:
            counts = storage.table_counts(s)
            for schema, n in sorted(counts.items()):
                mark = "[green]✓[/]" if schema in (s.schema, "public") else " "
                console.print(f"  {mark} schema {schema}: {n} table(s)")
            if counts.get(s.schema, 0) == 0:
                console.print(f"  [yellow]![/] schema {s.schema} is empty — "
                              "Dagster has not migrated into it yet")
        except ImportError:
            console.print("  [yellow]![/] psycopg2 missing; cannot inspect")
        except Exception as exc:  # noqa: BLE001
            console.print(f"  [red]✗[/] {type(exc).__name__}: {exc}")

    conf = _stack_dir() / "nginx.conf"
    console.print(f"[bold]front door[/]  "
                  f"{'rendered' if conf.exists() else '[yellow]not rendered[/]'}"
                  f" — {conf.relative_to(r) if conf.exists() else 'pf stack render'}")

    # Every probe goes through the front door, including the recce ones. Their
    # own ports are bound to loopback *inside* the container and are not
    # published, so probing them directly reports a connection error for a
    # server that is running perfectly — the cookie is how you address one.
    base = f"http://127.0.0.1:{frontdoor.LISTEN}"

    # The version that is *answering*, not the tag someone meant to build. An
    # upgrade that failed to take leaves a stack running the previous
    # distribution and reporting nothing wrong.
    try:
        with urllib.request.urlopen(  # noqa: S310
                f"{base}/api/v1/system/version", timeout=5) as resp:
            v = json.load(resp)
        console.print(f"[bold]openmetadata[/]  {v.get('version', '?')}"
                      f"  [dim]{str(v.get('revision', ''))[:8]}[/]")
    except Exception:  # noqa: BLE001 - not answering is reported by the table
        console.print("[bold]openmetadata[/]  [dim]not answering[/]")

    # Whether `catalog_sync` can publish, which is the difference between a
    # green Dagster run and 75 rejected writes. Reports where the credential
    # came from and never what it is.
    try:
        _, source = token.resolve(dict(os.environ),
                                  storage.admin_settings(s) if s else None)
        console.print(f"[bold]catalogue auth[/]  [green]✓[/] "
                      f"resolved from the {source}")
    except token.TokenUnavailable as exc:
        console.print(f"[bold]catalogue auth[/]  [yellow]![/] {exc}")

    svcs = frontdoor.services(all_projects())
    t = Table("what", "url", "state")
    probes: list[tuple[str, str, str]] = [
        ("catalogue", f"{base}/api/v1/system/version", ""),
        ("dagster", f"{base}/dagster/server_info", ""),
        ("launcher", f"{base}/pf/", ""),
    ]
    probes += [(f"recce/{x.project}", f"{base}/api/health", x.project)
               for x in svcs]
    for name, url, project in probes:
        req = urllib.request.Request(url)  # noqa: S310
        if project:
            req.add_header("Cookie", f"pf_recce={project}")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
                # The front door answers a stopped review server with the
                # explanatory page, not an error, so 200 alone is not "up".
                body = resp.read(400)
                state = ("[dim]stopped[/]" if b"not running" in body
                         else f"[green]{resp.status}[/]")
        except urllib.error.HTTPError as exc:
            # `^~ /api/` deliberately does not serve the explanatory HTML — a
            # JSON client should get a status, not a page — so a refused
            # upstream arrives here as 502, and for a review server that is the
            # normal resting state rather than a fault.
            state = ("[dim]stopped[/]" if project and exc.code == 502
                     else f"[yellow]{exc.code}[/]")
        except Exception as exc:  # noqa: BLE001
            state = f"[red]{type(exc).__name__}[/]"
        t.add_row(name, url, state)
    console.print(t)


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
    pdir(group, project)
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
    console.print("  Nothing is in effect yet. Review, edit, then approve:")
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


@sem_app.command("annotate")
def cmd_onto_annotate(
    group: str, project: str, pid: str,
    apply_: bool = typer.Option(False, "--apply", help="write contracts/annotations.yaml"),
    currency: str = typer.Option("", "--currency",
                                 help="ISO 4217 code for sources with money "
                                      "columns and no currency column"),
) -> None:
    """Draft a project's annotations from an ontology proposal's accepted axioms.

    The scan already established which table instantiates which class, what
    identifies it and what role each column plays. Retyping that by hand is not
    review, it is transcription, and on fifty raw tables it is where an
    onboarding quietly stops being done properly.

    Only accepted axioms are read. `links` stays empty until the relations are
    named and approved — a relation still called `refers_to` is a placeholder,
    and an annotation must not assert a link the ontology has not accepted.

    Existing entries are never overwritten, so this is safe to re-run as more of
    a proposal is approved.
    """
    from pf.ontology import proposal
    from pf.ontology.annotate import from_proposal, merge_annotations

    p = proposal.read(root(), group, pid)
    drafted = from_proposal(p, source=p.source, currency=currency.upper())
    if not drafted:
        console.print(f"[yellow]![/] nothing accepted in {pid} that implies an "
                      f"annotation — approve the class axioms first")
        raise typer.Exit(1)

    target = pdir(group, project) / "contracts" / "annotations.yaml"
    linked = sum(1 for a in drafted if a.links)
    console.print(f"[bold]{pid}[/] → {len(drafted)} annotation(s), "
                  f"{sum(len(a.roles) for a in drafted)} role(s), "
                  f"{linked} with links")
    if not apply_:
        for a in drafted[:5]:
            console.print(f"  [cyan]{a.resource}[/] → {a.concept} "
                          f"[dim]({len(a.roles)} role(s))[/]")
        console.print(f"  [dim]…and {max(0, len(drafted) - 5)} more[/]")
        console.print("\n[dim]draft only — re-run with --apply to write "
                      f"{target.relative_to(root())}[/]")
        raise typer.Exit(0)

    added, kept = merge_annotations(target, drafted)
    console.print(f"[green]✓[/] {target.relative_to(root())}: "
                  f"+{added} new, {kept} existing left untouched")
    if not linked:
        console.print("[yellow]![/] no links — the proposal's relations are still "
                      "placeholders. Name them after the business verb in the "
                      "proposal, approve, then re-run.")


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
def cmd_policy(group: str = typer.Argument("", help="resolve at this group's scope"),
               project: str = typer.Argument("", help="resolve at this project's scope")) -> None:
    """Policy chain: intent → constraint → artifact → evidence.

    With no argument this prints the platform floor. Naming a group, or a group
    and a project, resolves the layers over it — which is the only way to answer
    "what actually binds acme-eu", since a layer may tighten a policy the
    platform set and the platform file will not show it.
    """
    from pf.ontology.model import load_group_ontology, load_project_ontology

    if group and project:
        o, scope = load_project_ontology(root(), group, project), f"{group}/{project}"
    elif group:
        o, scope = load_group_ontology(root(), group), group
    else:
        o, scope = load_ontology(), "platform"
    console.print(f"[dim]scope:[/] {scope}")

    t = Table("policy", "severity", "set by", "constraint", "enforced by", "evidence")
    for p in o.policies:
        # Anything the local layers moved is the interesting row on this table.
        sev = p.severity if p.scope == "platform" else f"[yellow]{p.severity}[/]"
        t.add_row(p.id, sev, p.scope, p.constraint,
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
    from pf.projections.owl import export as export_owl
    from pf.projections.owl import stats

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
    from pf.projections.otop import build_manifest, stats
    from pf.projections.otop import export as export_otop

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
        console.print("\n[yellow]![/] licence review outstanding: "
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
    from pf.vendor.model import approve as approve_lock
    from pf.vendor.model import sync as vendor_sync

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
    console.print("[green]→[/] http://localhost:3000")
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
    from pf.pr import build as build_pr
    from pf.pr import markdown as pr_markdown
    from pf.pr import pr_number_from_env, save

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


# -------------------------------------------------------------- artefacts --
# Build output that is too big, too binary or too churn-heavy for git, in an
# S3-compatible bucket instead. See pf/artifacts.py for the layout and why, and
# docs/ARTIFACTS.md for the operator's side.
#
# The commands here are recce-shaped because recce is the only producer today.
# They are not recce-specific by accident of naming: `pf.artifacts` knows
# nothing about baselines, and a second producer adds its own key semantics
# there the same way `pf.tools.recce` did.
artifacts_app = typer.Typer(help="Publish and fetch build artefacts (R2/S3).")
app.add_typer(artifacts_app, name="artifacts")


def _recce_or_exit():  # the pf.tools.recce module, for its key semantics
    try:
        from pf.tools import recce
    except ImportError as exc:  # pragma: no cover - recce ships with pf
        console.print(f"[red]recce tool unavailable: {exc}[/]")
        raise typer.Exit(1)
    return recce


def _targets(group: str, project: str) -> list[tuple[str, str, Path]]:
    """One project, one group, or every project when nothing is given.

    The widening from "both or neither" is what lets the graph commands be run
    the way they are actually needed — `pf kg build` after adding a project
    anywhere, `pf kg build acme` after changing something a family shares. A
    command that can only be pointed at one project at a time gets run for the
    project you remembered, which is how seven graphs end up a month stale.
    """
    if group and project:
        return [(group, project, pdir(group, project))]
    if project:
        console.print("[red]a project needs its group[/]")
        raise typer.Exit(1)
    if group:
        hits = [(g, p, d) for g, p, d in all_projects() if g == group]
        if not hits:
            console.print(f"[red]group {group} has no projects[/]")
            raise typer.Exit(1)
        return hits
    return all_projects()


def _store_or_exit(art):  # `art` is the pf.artifacts module
    """A configured store, or a one-line exit.

    Unconfigured is the *expected* first state of these commands, not a bug, so
    it gets the setup hint rather than a NotConfigured traceback with the
    hint buried at the bottom of it.
    """
    store = art.Store.from_env()
    if store is None:
        console.print(f"[yellow]{art.SETUP_HINT}[/]")
        raise typer.Exit(1)
    return store


@artifacts_app.command("status")
def cmd_artifacts_status() -> None:
    """Is a store configured, and can we reach it?"""
    from pf import artifacts as art

    store = art.Store.from_env()
    if store is None:
        console.print("[yellow]not configured[/]")
        console.print(f"  {art.SETUP_HINT}")
        console.print(f"  [dim]endpoint would be {art.DEFAULT_ENDPOINT}[/]")
        console.print(f"  [dim]bucket   would be {art.DEFAULT_BUCKET}[/]")
        raise typer.Exit(1)

    d = store.describe()
    t = Table("field", "value", title="artefact store")
    for k in ("endpoint", "bucket", "key_id", "source"):
        t.add_row(k, d[k])
    t.add_row("base ref", art.base_ref())
    t.add_row("head ref", art.head_ref(root()))
    console.print(t)

    why = store.check()
    if why:
        console.print(f"[red]unreachable:[/] {why}")
        raise typer.Exit(1)
    console.print("[green]✓[/] reachable")


@artifacts_app.command("push")
def cmd_artifacts_push(group: str = typer.Argument(""), project: str = typer.Argument(""),
                       ref: str = typer.Option("", "--ref", help="override the ref key segment"),
                       baseline: bool = typer.Option(True, "--baseline/--no-baseline"),
                       review: bool = typer.Option(True, "--review/--no-review")) -> None:
    """Upload a project's recce artefacts. No arguments → every project."""
    from pf import artifacts as art

    store = _store_or_exit(art)
    recce = _recce_or_exit()
    moved = 0
    for g, p, d in _targets(group, project):
        rows = []
        if baseline:
            rows += art.push_files(store, recce.baseline_pairs(d, g, p, ref))
        if review:
            rows += art.push_files(store, recce.review_pairs(d, g, p, ref))
        if not rows:
            console.print(f"[dim]{g}/{p} — nothing on disk to publish[/]")
            continue
        console.print(f"[green]✓[/] {g}/{p}")
        for t in rows:
            console.print(f"  ↑ {t.key} [dim]({art.human(t.size)})[/]")
        moved += len(rows)
    console.print(f"[dim]{moved} object(s)[/]")


@artifacts_app.command("pull")
def cmd_artifacts_pull(group: str = typer.Argument(""), project: str = typer.Argument(""),
                       ref: str = typer.Option("", "--ref", help="override the ref key segment"),
                       baseline: bool = typer.Option(True, "--baseline/--no-baseline"),
                       review: bool = typer.Option(True, "--review/--no-review")) -> None:
    """Download a project's recce artefacts. No arguments → every project.

    Overwrites what is on disk. That is the point — this is how a fresh clone
    gets a baseline — but it means a locally captured baseline you have not
    published is replaced by whatever the trunk published. `--no-baseline` when
    you only want the review.
    """
    from pf import artifacts as art

    store = _store_or_exit(art)
    recce = _recce_or_exit()
    got = missed = 0
    for g, p, d in _targets(group, project):
        pairs = []
        if baseline:
            pairs += recce.baseline_pairs(d, g, p, ref)
        if review:
            pairs += recce.review_pairs(d, g, p, ref)
        try:
            rows = art.pull_files(store, pairs)
        except art.ArtifactStoreError as exc:
            console.print(f"[red]{exc}[/]")
            raise typer.Exit(1)
        console.print(f"[green]✓[/] {g}/{p}" if any(t.ok for t in rows)
                      else f"[yellow]·[/] {g}/{p} [dim]nothing published[/]")
        for t in rows:
            if t.ok:
                console.print(f"  ↓ {t.path} [dim]({art.human(t.size)})[/]")
                got += 1
            else:
                console.print(f"  [dim]· {t.key} — absent[/]")
                missed += 1
    console.print(f"[dim]{got} fetched, {missed} absent[/]")


@artifacts_app.command("ls")
def cmd_artifacts_ls(group: str = typer.Argument(""), project: str = typer.Argument(""),
                     prefix: str = typer.Option("", "--prefix",
                                                help="raw key prefix, instead of a project")) -> None:
    """What is in the bucket."""
    from pf import artifacts as art

    store = _store_or_exit(art)
    if prefix:
        pfx = prefix
    elif group and project:
        pfx = art.project_prefix(group, project)
    else:
        pfx = ""

    rows = store.ls(pfx)
    if not rows:
        console.print(f"[yellow]nothing under[/] {store.url(pfx)}")
        return
    t = Table("key", "size", "modified", title=store.url(pfx))
    for r in sorted(rows, key=lambda r: str(r["key"])):
        t.add_row(str(r["key"]), art.human(int(r["size"])), str(r["modified"])[:19])
    console.print(t)
    console.print(f"[dim]{len(rows)} object(s), "
                  f"{art.human(sum(int(r['size']) for r in rows))}[/]")


@artifacts_app.command("migrate")
def cmd_artifacts_migrate(group: str = typer.Argument(""), project: str = typer.Argument(""),
                          apply: bool = typer.Option(False, "--apply",
                                                     help="actually push and untrack")) -> None:
    """Move committed recce artefacts out of git and into the store.

    Push, verify every key landed, and only then `git rm --cached`. The order is
    the whole safety of this command: untracking first and uploading second
    would, on a failed upload, leave the artefacts nowhere. They would still be
    in git history and recoverable, but "recoverable from history" is not a
    state to leave a merge gate in.

    Dry by default. `--apply` does it.
    """
    from pf import artifacts as art

    store = _store_or_exit(art)
    recce = _recce_or_exit()
    rel = root()
    plan: list[tuple[str, str, list[tuple[str, Path]]]] = []

    for g, p, d in _targets(group, project):
        pairs = [(k, f) for k, f in
                 recce.baseline_pairs(d, g, p) + recce.review_pairs(d, g, p)
                 if f.is_file()]
        tracked = [(k, f) for k, f in pairs if _git_tracked(f, rel)]
        if tracked:
            plan.append((g, p, tracked))

    if not plan:
        console.print("[green]nothing to migrate[/] — no tracked recce artefacts")
        return

    total = sum(f.stat().st_size for _, _, ts in plan for _, f in ts)
    for g, p, tracked in plan:
        console.print(f"[bold]{g}/{p}[/]")
        for k, f in tracked:
            console.print(f"  {f.relative_to(rel)} [dim]({art.human(f.stat().st_size)})"
                          f" → {store.url(k)}[/]")
    console.print(f"[dim]{sum(len(t) for _, _, t in plan)} file(s), "
                  f"{art.human(total)}[/]")

    if not apply:
        console.print("\n[yellow]dry run[/] — re-run with --apply to push and untrack")
        return

    for g, p, tracked in plan:
        for k, f in tracked:
            store.put(k, f)
        # Verify before removing. `put` raising is the common failure; a silent
        # partial write is the one that would cost data, so the check is a
        # round trip to the bucket rather than trust in the call that returned.
        absent = [k for k, _ in tracked if not store.exists(k)]
        if absent:
            console.print(f"[red]{g}/{p}: not in the bucket after upload — "
                          f"{', '.join(absent)}. Left tracked.[/]")
            raise typer.Exit(1)
        paths = [str(f.relative_to(rel)) for _, f in tracked]
        proc = subprocess.run(["git", "rm", "--cached", "-q", "--", *paths],
                              cwd=str(rel), capture_output=True, text=True,
                              check=False)
        if proc.returncode != 0:
            console.print(f"[red]{g}/{p}: git rm --cached failed: "
                          f"{proc.stderr.strip()}[/]")
            raise typer.Exit(1)
        console.print(f"[green]✓[/] {g}/{p} — {len(tracked)} published and untracked")

    console.print("\n[bold]Next:[/] add the ignore rules, drop the "
                  "`denylist_except` entries for these paths in gate.yaml, and "
                  "commit the removals. `pf check` will flag any that are still "
                  "tracked.")


def _git_tracked(path: Path, cwd: Path) -> bool:
    proc = subprocess.run(["git", "ls-files", "--error-unmatch", "--", str(path)],
                          cwd=str(cwd), capture_output=True, text=True, check=False)
    return proc.returncode == 0


# ------------------------------------------------------------------ tools --
# Tools are capabilities that also *run*. The sub-app below knows about tools in
# general and about no tool in particular: every row comes from the registry, so
# a tool installed from outside this repo appears here without an edit.
tool_app = typer.Typer(help="Pluggable tools: dbt review, BI, whatever is installed.")
app.add_typer(tool_app, name="tool")

# ------------------------------------------------------------- test index --
test_app = typer.Typer(help="What the test suite guards, without reading it.")
app.add_typer(test_app, name="test")


def _tests_dir() -> Path:
    return root() / "platform" / "tests"


@test_app.command("index")
def cmd_test_index() -> None:
    """Regenerate `platform/tests/README.md` from the suite's own docstrings."""
    from pf.testmap import index_path, render_index, scan

    files = scan(_tests_dir())
    out = index_path(_tests_dir())
    content = render_index(files)
    changed = not out.exists() or out.read_text() != content
    out.write_text(content)
    console.print(f"[green]✓[/] {out.relative_to(root())}  "
                  f"[dim]({len(files)} files, {sum(f.tests for f in files)} tests"
                  f"{'' if changed else ' · already current'})[/]")


@test_app.command("where")
def cmd_test_where(term: str) -> None:
    """Which tests cover this? Searches subjects, filenames and imported modules."""
    from pf.testmap import scan, where

    hits = where(scan(_tests_dir()), term)
    if not hits:
        console.print(f"No test file mentions '{term}'.")
        raise typer.Exit(1)
    t = Table("file", "guards", "tests", title=f"{len(hits)} file(s) for '{term}'")
    for f in hits:
        t.add_row(f"{f.group}/{f.path.name}" if f.group else f.path.name,
                  f.subject[:64], str(f.tests))
    console.print(t)


@test_app.command("check")
def cmd_test_check() -> None:
    """Is the committed index current with the suite?

    An index generated before a test file was added answers "where is that
    tested" with confident silence, which is worse than having no index.
    """
    from pf.testmap import drift

    reason = drift(_tests_dir())
    if reason:
        console.print(f"[red]✗[/] {reason}")
        raise typer.Exit(1)
    console.print("[green]✓[/] the test index matches the suite")


@tool_app.command("list")
def cmd_tool_list(group: str = typer.Argument("", help="show enablement for a project"),
                  project: str = typer.Argument("")) -> None:
    """Every registered tool, and where it is enabled."""
    from pf.tools import discover, readiness

    found, errors = discover()
    if group and project:
        rows = readiness(root(), group, project)
        t = Table("tool", "enabled", "from", "installed", "ready", "blockers",
                  title=f"tools · {group}/{project}")
        for r in rows:
            t.add_row(
                r["name"],
                "[green]yes[/]" if r["enabled"] else "[dim]no[/]",
                r["source"] if r["enabled"] else "—",
                "[green]yes[/]" if r["installed"] else "[yellow]no[/]",
                "[green]✓[/]" if r["ready"] else "[dim]·[/]",
                "; ".join(r["blockers"]) or (r["hint"] if not r["installed"] else ""),
            )
        console.print(t)
    else:
        t = Table("tool", "scope", "installed", "surface", "description")
        for name, tool in sorted(found.items()):
            t.add_row(name, ",".join(sorted(tool.scope)),
                      "[green]yes[/]" if tool.installed else "[yellow]no[/]",
                      tool.surface.url() if tool.surface else "—", tool.summary)
        console.print(t)
    for e in errors:
        console.print(f"  [red]✗[/] {e}")
    console.print("[dim]Adding one is a `TOOL` object plus an entry in "
                  "pf.tools.registry.BUILTIN_MODULES — or a `pf.tools` entry point "
                  "in any installed package, which needs no edit here.[/]")


@tool_app.command("enable")
def cmd_tool_enable(tool: str, group: str,
                    project: str = typer.Argument("", help="omit to enable for the whole group"),
                    scaffold: bool = typer.Option(True, help="apply the capability and bootstrap")) -> None:
    """Turn a tool on for a group (every sister) or one project."""
    from pf.tools import get as get_tool
    from pf.tools import write as write_tool_config
    from pf.tools.spec import InvalidTool

    try:
        t = get_tool(tool)
    except InvalidTool as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(1)

    level = "project" if project else "group"
    if not t.supports(level):
        console.print(f"[red]{tool} cannot be enabled at {level} level[/] "
                      f"(scope: {', '.join(sorted(t.scope))})")
        raise typer.Exit(1)

    path = write_tool_config(root(), group, project, tool, on=True)
    console.print(f"[green]✓[/] {tool} enabled for "
                  f"[bold]{group}{'/' + project if project else ' (all sisters)'}[/]")
    console.print(f"  [dim]{path}[/]")

    if not scaffold:
        return
    # The capability half — files, settings, gate rules — goes through exactly the
    # same path `pf capability-add` uses, so there is one scaffolder and one gate
    # merge rather than a second way to write into a project.
    targets = [(group, project)] if project else [
        (g, p) for g, p, _ in all_projects() if g == group]
    for g, p in targets:
        d = pdir(g, p)
        if t.capability is not None:
            ctx = {"group": g, "project": p, "module": p.replace("-", "_")}
            written = apply_capability(t.capability, root(), d, ctx)
            console.print(f"  [green]+[/] {g}/{p} ({len(written)} file(s))")
    if t.capability is not None:
        _merge_gate_rules(t.gate_sections())
    for g, p in targets:
        console.print(f"[bold]{g}/{p}[/]")
        _print_bootstrap(bootstrap(root(), g, p))


@tool_app.command("disable")
def cmd_tool_disable(tool: str, group: str, project: str = typer.Argument("")) -> None:
    """Turn a tool off. Generated files are left in place, deliberately —
    deleting them on disable would throw away a recorded review."""
    from pf.tools import write as write_tool_config

    path = write_tool_config(root(), group, project, tool, on=False)
    console.print(f"[green]✓[/] {tool} disabled for "
                  f"{group}{'/' + project if project else ' (group default)'}")
    console.print(f"  [dim]{path}[/]")


@tool_app.command("doctor")
def cmd_tool_doctor(group: str = typer.Argument(""), project: str = typer.Argument(""),
                    all_: bool = typer.Option(False, "--all")) -> None:
    """Why is a tool not doing anything? Registered, enabled, installed, ready."""
    from pf.tools import readiness

    targets = all_projects() if all_ else [(group, project, pdir(group, project))]
    if not all_ and not (group and project):
        console.print("[red]give a group and project, or --all[/]")
        raise typer.Exit(1)

    problems = 0
    for g, p, _ in targets:
        rows = [r for r in readiness(root(), g, p) if r["enabled"]]
        if not rows:
            console.print(f"[dim]{g}/{p}: no tools enabled[/]")
            continue
        console.print(f"[bold]{g}/{p}[/]")
        for r in rows:
            if r["ready"]:
                console.print(f"  [green]✓[/] {r['name']:12} ready  [dim]{r['surface']}[/]")
                continue
            problems += 1
            reason = ("; ".join(r["blockers"]) or r["hint"]
                      or f"missing {', '.join(r['missing'])}")
            console.print(f"  [yellow]![/] {r['name']:12} {reason}")
    raise typer.Exit(1 if problems else 0)


def _register_tool_commands() -> None:
    """Let each tool attach its own subcommands under `pf tool <name>`.

    Hooks are resolved one at a time and failures are contained: a third-party
    tool with a broken CLI hook must not stop `pf` from starting, because the
    command you need at that moment is probably `pf tool doctor`.
    """
    from pf.tools import all_tools

    for name, tool in sorted(all_tools().items()):
        try:
            hook = tool.hook("commands")
            if hook is not None:
                hook(tool_app)
        except Exception as exc:  # noqa: BLE001 — a broken tool CLI is not fatal
            console.print(f"[dim]tool '{name}' registered no commands: "
                          f"{type(exc).__name__}[/]", highlight=False)


_register_tool_commands()


if __name__ == "__main__":
    app()
