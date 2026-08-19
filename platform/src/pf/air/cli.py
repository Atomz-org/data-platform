"""The `pf air` command group.

Kept beside the catalogue layer rather than in `pf.cli`, so adding a command is
one file. `pf.cli` does `app.add_typer(air_app, name="air")` and nothing else.

Every command degrades rather than raising when no catalogue is checked out: a
clone without submodules must still be able to run `pf air coverage` and be told
why it says nothing, because the alternative is a traceback that reads like a
bug in the platform.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()

air_app = typer.Typer(
    help="AI risk taxonomy and control catalogue, and our coverage of it.")

_AIR_MARK = {"pass": ("green", "\u2713"), "fail": ("red", "\u2717"),
             "unexercised": ("yellow", "?")}


def root() -> Path:
    from pf.cli import root as _root

    return _root()


def _air_catalogue():
    """The catalogue, or a clean exit explaining the submodule is not checked out."""
    from pf.air import absent_reason, available, load

    if not available(root()):
        console.print(f"[yellow]{absent_reason(root())}[/]")
        raise typer.Exit(0)
    return load(root())


def _air_coverage(group: str = "", project: str = ""):
    from pf.air import absent_reason, assess

    cov = assess(root(), group, project)
    if not cov.vendored:
        console.print(f"[yellow]{absent_reason(root())}[/]")
        raise typer.Exit(0)
    return cov


@air_app.command("risks")
def cmd_air_risks(kind: str = typer.Option("", "--type", "-t",
                                           help="RC | OP | SEC")) -> None:
    """The risk taxonomy, with the controls that claim each one."""
    cat = _air_catalogue()
    rows = cat.risks_of_type(kind) if kind else cat.sorted_risks
    if not rows:
        console.print(f"[dim]no risks of type '{kind}'[/]")
        raise typer.Exit(1)

    table = Table(box=None, pad_edge=False)
    for col in ("id", "type", "title", "mitigated by"):
        table.add_column(col, overflow="fold")
    for r in rows:
        controls = cat.controls_for(r.id)
        table.add_row(r.id, r.type_label, r.title,
                      ", ".join(c.id for c in controls) or "[red]nothing[/]")
    console.print(table)
    console.print(f"\n[dim]{len(rows)} risk(s) · pinned at {cat.commit[:12]}[/]")


@air_app.command("controls")
def cmd_air_controls(kind: str = typer.Option("", "--type", "-t",
                                              help="PREV | DET | RESP"),
                     risk: str = typer.Option("", "--risk",
                                              help="only controls mitigating this risk"),
                     ) -> None:
    """The control catalogue."""
    cat = _air_catalogue()
    rows = cat.controls_of_type(kind) if kind else cat.sorted_controls
    if risk:
        target = risk.strip().upper()
        rows = tuple(c for c in rows if target in c.mitigates)
    if not rows:
        console.print("[dim]no controls match[/]")
        raise typer.Exit(1)

    table = Table(box=None, pad_edge=False)
    for col in ("id", "type", "title", "mitigates"):
        table.add_column(col, overflow="fold")
    for c in rows:
        table.add_row(c.id, c.type_label, c.title, ", ".join(c.mitigates))
    console.print(table)
    console.print(f"\n[dim]{len(rows)} control(s) · pinned at {cat.commit[:12]}[/]")


@air_app.command("show")
def cmd_air_show(doc_id: str) -> None:
    """One risk or control: what it is, what it links to, what it cites."""
    cat = _air_catalogue()
    d = cat.get(doc_id)
    if d is None:
        console.print(f"[red]{doc_id}[/] is not in the catalogue. "
                      f"`pf air risks` / `pf air controls` list them.")
        raise typer.Exit(1)

    console.print(f"[bold]{d.id}[/]  {d.title}")
    console.print(f"[dim]{d.type_label} · {d.doc_status} · {d.path}[/]\n")
    if d.summary:
        console.print(d.summary + "\n")

    mitigates = getattr(d, "mitigates", ())
    if mitigates:
        console.print("[bold]mitigates[/]")
        for rid in mitigates:
            r = cat.risks.get(rid)
            console.print(f"  {rid:12} {r.title if r else '[red]not in catalogue[/]'}")
        console.print()
    else:
        covered = cat.controls_for(d.id)
        if covered:
            console.print("[bold]mitigated by[/]")
            for c in covered:
                console.print(f"  {c.id:12} {c.title}")
            console.print()

    if d.references:
        console.print("[bold]external references[/]")
        for fw in d.frameworks:
            regime = cat.regimes.get(fw)
            console.print(f"  [cyan]{regime.title if regime else fw}[/]")
            for ref in d.refs_for(fw):
                if ref.resolved:
                    console.print(f"    {ref.title}")
                    if ref.url:
                        console.print(f"      [dim]{ref.url}[/]")
                elif ref.malformed:
                    console.print(f"    [yellow]{ref.key}[/] [dim]— upstream frontmatter "
                                  f"defect, not a real citation (`pf air verify`)[/]")
                else:
                    console.print(f"    [red]{ref.key}[/] [dim]— unresolved[/]")


@air_app.command("coverage")
def cmd_air_coverage(group: str = typer.Argument(""), project: str = typer.Argument(""),
                     markdown: bool = typer.Option(False, "--markdown", "-m",
                                                   help="GitHub job-summary format"),
                     ) -> None:
    """Which controls this platform actually discharges. Derived on every run.

    Nothing is stored — a verdict is recomputed from the repository each time,
    because a recorded pass survives the change that invalidated it.
    """
    cov = _air_coverage(group, project)
    c = cov.counts

    if markdown:
        print("### AI control coverage\n")
        print(f"{c['pass']} enforced · {c['fail']} not enforced · "
              f"{c['unexercised']} unexercised · {c['total']} total\n")
        print("| | control | title | evidence |")
        print("| --- | --- | --- | --- |")
        for v in cov:
            mark = {"pass": "✅", "fail": "❌", "unexercised": "⚠️"}[v.status]
            print(f"| {mark} | {v.id} | {v.control.title} | {v.check.evidence} |")
        raise typer.Exit(0)

    table = Table(box=None, pad_edge=False)
    for col in ("", "control", "title", "evidence"):
        table.add_column(col, overflow="fold")
    for v in cov:
        style, glyph = _AIR_MARK[v.status]
        table.add_row(f"[{style}]{glyph}[/]", v.id, v.control.title,
                      f"[dim]{v.check.evidence}[/]")
    console.print(table)
    console.print(f"\n[green]{c['pass']} enforced[/] · [red]{c['fail']} not enforced[/] · "
                  f"[yellow]{c['unexercised']} unexercised[/] of {c['total']}")
    console.print("[dim]`pf air gaps` for what is missing · "
                  "`pf air crosswalk eu-ai-act` for the regulatory view[/]")


@air_app.command("gaps")
def cmd_air_gaps(group: str = typer.Argument(""), project: str = typer.Argument("")) -> None:
    """Only the controls that are not enforced, most-cited regime first."""
    cov = _air_coverage(group, project)
    gaps = cov.failing
    if not gaps:
        console.print("[green]no gaps[/] — every control in the catalogue is enforced")
        raise typer.Exit(0)

    for v in sorted(gaps, key=lambda x: -len(x.control.references)):
        console.print(f"[red]✗[/] [bold]{v.id}[/]  {v.control.title}")
        console.print(f"    [dim]{v.check.evidence}[/]")
        if v.control.references:
            regimes = ", ".join(v.control.frameworks)
            console.print(f"    [dim]cited by: {regimes} "
                          f"({len(v.control.references)} references)[/]")
        console.print()
    console.print(f"[red]{len(gaps)}[/] of {len(cov)} controls not enforced.")
    console.print("[dim]A gap is only a merge blocker when an air.yaml `baseline` "
                  "names it — `pf air gate <group> <project>`.[/]")


@air_app.command("crosswalk")
def cmd_air_crosswalk(framework: str = typer.Argument(
        ..., help="eu-ai-act | iso-42001 | nist-sp-800-53r5 | owasp-llm | ...")) -> None:
    """One external regime, and which of our policies discharges each citation."""
    cat = _air_catalogue()
    name = framework.strip().lower()
    if name not in cat.regimes:
        console.print(f"[red]{framework}[/] is not a regime in this corpus. "
                      f"Known: {', '.join(sorted(cat.regimes))}")
        raise typer.Exit(1)

    cov = _air_coverage()
    regime = cat.regimes[name]
    console.print(f"[bold]{regime.title}[/]")
    if regime.description:
        console.print(f"[dim]{regime.description}[/]")
    console.print()

    # Citation -> the controls that cite it -> our verdict on those controls.
    by_key: dict[str, list] = {}
    for d in (*cat.sorted_risks, *cat.sorted_controls):
        for ref in d.refs_for(name):
            if ref.resolved:
                by_key.setdefault(ref.key, []).append(d)

    table = Table(box=None, pad_edge=False)
    for col in ("", "citation", "via", "our policies"):
        table.add_column(col, overflow="fold")
    for key in sorted(by_key):
        docs = by_key[key]
        controls = [d for d in docs if d.id.startswith(("AIR-PREV", "AIR-DET", "AIR-RESP"))]
        verdicts = [cov.get(c.id) for c in controls]
        verdicts = [v for v in verdicts if v is not None]
        if not verdicts:
            style, glyph = "dim", "·"
            policies = "[dim]risk only — no control cites this[/]"
        else:
            worst = ("fail" if any(v.status == "fail" for v in verdicts)
                     else "unexercised" if any(v.status == "unexercised" for v in verdicts)
                     else "pass")
            style, glyph = _AIR_MARK[worst]
            names = sorted({p for v in verdicts for p in v.policies})
            policies = ", ".join(names) or "[red]none[/]"
        title = cat.regimes[name].entries.get(key, {}).get("title", key)
        table.add_row(f"[{style}]{glyph}[/]", str(title),
                      ", ".join(d.id for d in docs), policies)
    console.print(table)
    console.print(f"\n[dim]{len(by_key)} cited provision(s) of {len(regime.entries)} "
                  f"in the regime. Uncited provisions are outside the framework's "
                  f"scope, not gaps in ours.[/]")


@air_app.command("verify")
def cmd_air_verify() -> None:
    """Check the vendored corpus against its own frontmatter contract."""
    from pf.air import verify

    rep = verify(root())
    if not rep.vendored:
        for f in rep.findings:
            console.print(f"[yellow]{f.detail}[/]")
        raise typer.Exit(0)

    for f in rep.findings:
        colour = {"ok": "green", "warn": "yellow", "fail": "red"}[f.level]
        console.print(f"[{colour}]{f.level}[/] [bold]{f.code}[/]\n    {f.detail}\n")
    console.print(f"[dim]{rep.risks} risks · {rep.controls} controls · "
                  f"{rep.references} citations · {rep.regimes} regimes · "
                  f"pinned at {rep.commit[:12]}[/]")
    raise typer.Exit(rep.exit_code)


@air_app.command("register")
def cmd_air_register(group: str, project: str,
                     show: bool = typer.Option(False, "--show",
                                               help="print instead of writing"),
                     ) -> None:
    """Regenerate `governance/air-register.md` from air.yaml and a coverage run."""
    from pf.air import RegisterError, render_register
    from pf.air.register import write_register

    try:
        if show:
            console.print(render_register(root(), group, project))
            return
        out = write_register(root(), group, project)
    except RegisterError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(1) from exc
    console.print(f"[green]wrote[/] {out.relative_to(root())}")


@air_app.command("gate")
def cmd_air_gate(group: str, project: str) -> None:
    """Block when a control this entity committed to is not enforced.

    Blocks on `fail` only. `unexercised` warns and exits zero — walling a project
    off because a ledger has not been written yet is how a gate stops being run.
    """
    from pf.air.register import gate

    res = gate(root(), group, project)
    if not res.vendored:
        console.print("[yellow]catalogue not checked out — nothing assessed[/]")
        raise typer.Exit(0)

    for p in res.problems:
        console.print(f"[red]declaration:[/] {p}")
    for cid, why in res.warned:
        console.print(f"[yellow]?[/] {cid} [dim]— {why}[/]")
    for cid, why in res.breaches:
        console.print(f"[red]✗[/] [bold]{cid}[/] [dim]— {why}[/]")

    if res.ok:
        console.print(f"[green]baseline met[/] — {res.assessed} committed control(s), "
                      f"{len(res.warned)} unexercised")
    else:
        console.print(f"\n[red]{len(res.breaches)} committed control(s) not enforced[/] "
                      f"of {res.assessed}. Fix the control, or move it to `accepted:` "
                      f"in air.yaml with a reason and an owner.")
    raise typer.Exit(res.exit_code)




@air_app.command("catalogues")
def cmd_air_catalogues() -> None:
    """Which control catalogues are registered, and which are on disk.

    `pf.air` reads catalogues, not one framework. A second one is a
    `CatalogueSource` on the `pf.catalogues` entry point of any installed
    distribution — no edit to this platform.
    """
    from pf.air.sources import discover

    sources, errors = discover()
    if not sources and not errors:
        console.print("[yellow]no control catalogue is registered[/]")
        raise typer.Exit(0)

    table = Table(box=None, pad_edge=False)
    for col in ("", "name", "prefix", "title", "path", "licence"):
        table.add_column(col, overflow="fold")
    for s in sources.values():
        on_disk = s.available(root())
        style, glyph = ("green", "✓") if on_disk else ("yellow", "?")
        table.add_row(f"[{style}]{glyph}[/]", s.name, s.prefix, s.title,
                      f"[dim]{s.path}[/]", s.licence or "—")
    console.print(table)

    for e in errors:
        console.print(f"[red]✗[/] {e.source} [dim]— {e.error}[/]")

    missing = [s for s in sources.values() if not s.available(root())]
    if missing:
        console.print(f"\n[dim]? not checked out — `git submodule update --init "
                      f"{' '.join(s.path for s in missing)}`[/]")
    raise typer.Exit(1 if errors else 0)


@air_app.command("baseline")
def cmd_air_baseline(group: str, project: str = typer.Argument(""),
                     suggest: bool = typer.Option(False, "--suggest",
                                                  help="propose the controls that already pass"),
                     ) -> None:
    """What this entity has committed to — or, with --suggest, what it could.

    `--suggest` prints the controls that currently pass and are not already
    declared, ready to paste into `air.yaml`. It deliberately does not write the
    file: committing to a control is a decision with an owner, and a scaffolder
    that makes it silently produces commitments nobody made.
    """
    from pf.air import absent_reason, available, load, load_config
    from pf.air.coverage import assess
    from pf.air.register import validate

    if not available(root()):
        console.print(f"[yellow]{absent_reason(root())}[/]")
        raise typer.Exit(0)

    cat = load(root())
    cfg = load_config(root(), group, project)
    label = f"{group}/{project}" if project else group

    if not suggest:
        console.print(f"[bold]{label}[/] [dim]— from {', '.join(cfg.sources) or 'no air.yaml'}[/]\n")
        if cfg.profile:
            for k, v in cfg.profile.items():
                console.print(f"  [dim]{k}[/] {v}")
            console.print()
        console.print(f"[bold]committed[/] ({len(cfg.baseline)})")
        for cid in cfg.baseline:
            ctl = cat.controls.get(cid)
            console.print(f"  {cid:14} {ctl.title if ctl else '[red]not in catalogue[/]'}")
        if cfg.accepted:
            console.print(f"\n[bold]accepted[/] ({len(cfg.accepted)})")
            for a in cfg.accepted:
                due = f" [dim]review {a.review_by}[/]" if a.review_by else ""
                overdue = " [red]overdue[/]" if a.overdue else ""
                console.print(f"  {a.control:14} {a.owner}{due}{overdue}")
        for p in validate(cfg, cat):
            console.print(f"[red]![/] {p}")
        raise typer.Exit(0)

    cov = assess(root(), group, project, catalogue=cat)
    already = set(cfg.baseline) | cfg.accepted_ids
    fresh = [v for v in cov.passing if v.id not in already]
    if not fresh:
        console.print(f"[green]nothing to add[/] — {label} already commits to every "
                      f"control that passes")
        raise typer.Exit(0)

    console.print(f"[dim]# {len(fresh)} control(s) currently passing and not yet declared.[/]")
    console.print(f"[dim]# Paste into groups/{group}/air.yaml (or the project's) "
                  f"under `baseline:`.[/]")
    console.print("[dim]# Committing to a control is a decision — review each line.[/]\n")
    for v in fresh:
        console.print(f"  - {v.id:14} # {v.control.title}")
    console.print(f"\n[dim]{len(cov.failing)} control(s) still failing "
                  f"(`pf air gaps`) — those would block the merge if declared.[/]")
