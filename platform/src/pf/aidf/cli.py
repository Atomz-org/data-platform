"""The `pf govern` and `pf dora` command groups.

Beside the package rather than in `pf.cli`, the way `pf air` is: `pf.cli`
does `app.add_typer(govern_app, name="govern")` and
`app.add_typer(dora_app, name="dora")` and nothing else.

Exit codes are the contract CI reads: 0 for PASS or a clean audit, 1 for a
REJECT, a failing audit or a config that will not load, 2 for ESCALATED
(waiting on a person), 3 for CIRCUIT_BROKEN.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()

govern_app = typer.Typer(help="Runtime AI governance: contracts, validators, the action gate and the breaker.")
dora_app = typer.Typer(help="DORA (EU 2022/2554) evidence: infrastructure, supply chain, ledger, repository.")

EXIT = {"PASS": 0, "REJECT": 1, "ESCALATED": 2, "CIRCUIT_BROKEN": 3}
_MARK = {"pass": "[green]PASS[/]", "fail": "[red]FAIL[/]", "unverified": "[yellow]UNVERIFIED[/]",
         "not_applicable": "[dim]N/A[/]"}


def root() -> Path:
    from pf.cli import root as _root

    return _root()


def _entities(group: str | None, project: str | None) -> list[tuple[str, str]]:
    from pf.aidf.config import entities

    if group and project:
        return [(group, project)]
    if group:
        return [(g, p) for g, p in entities(root()) if g == group]
    return entities(root())


# ------------------------------------------------------------------ govern --
@govern_app.command("check")
def govern_check(group: str | None = typer.Argument(None), project: str | None = typer.Argument(None),
                 as_json: bool = typer.Option(False, "--json")) -> None:
    """Resolve every entity's governance config and refuse one that loosens the floor.

    The CI step. A project scaffolded before the capability existed still
    resolves — to the floor — so "no file" is never "no governance".
    """
    from pf.aidf.config import AidfConfigError
    from pf.aidf.engine import GovernanceEngine

    rows, failed = [], False
    for g, p in _entities(group, project):
        try:
            desc = GovernanceEngine(root(), g, p).describe()
            rows.append({"group": g, "project": p, "ok": True, **desc})
        except AidfConfigError as exc:
            failed = True
            rows.append({"group": g, "project": p, "ok": False, "error": str(exc)})
    if as_json:
        print(json.dumps(rows, indent=2, default=str))
    else:
        t = Table(box=None, pad_edge=False)
        for col in ("entity", "layers", "dialect", "validators", "roles", "breaker"):
            t.add_column(col, overflow="fold")
        for r in rows:
            if not r["ok"]:
                t.add_row(f"{r['group']}/{r['project']}", f"[red]{r['error']}[/]", "", "", "", "")
                continue
            br = r["breaker"]
            t.add_row(f"{r['group']}/{r['project']}", str(len(r["layers"])), r["dialect"],
                      ",".join(r["validators"]), ",".join(r["roles"]),
                      "[red]open[/]" if br["open"] else f"closed ({br['consecutive_failures']}/{br['limit']})")
        console.print(t)
        console.print(f"\n[dim]{len(rows)} entity(ies) · {'[red]config errors[/]' if failed else 'all resolve'}[/]")
    raise typer.Exit(1 if failed else 0)


@govern_app.command("evaluate")
def govern_evaluate(
    group: str, project: str,
    payload: str = typer.Option(..., "--payload", "-p", help="JSON file, or - for stdin"),
    role: str = typer.Option(..., "--role", "-r", help="The agent role submitting (see aidf.yaml roles)"),
    target: str = typer.Option("", "--target", "-t",
                               help="Project-relative path to write; default derives from the payload"),
    contract: str = typer.Option("mart_metric", "--contract", "-c", help="mart_metric | semantic_model"),
    columns: str = typer.Option("", "--columns",
                                help="Comma-separated catalogue columns; default reads the knowledge graph"),
    write: bool = typer.Option(True, "--write/--no-write", help="Write the validated record on PASS"),
    approved: str = typer.Option("", "--approved", help="Action id a person approved, for an elevated target"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Gate, validate, record — one agent payload through the whole engine."""
    from pf.aidf.engine import BudgetExceeded, GovernanceEngine

    raw = sys.stdin.read() if payload == "-" else Path(payload).read_text(encoding="utf-8")
    cols = {c.strip() for c in columns.split(",") if c.strip()} or None
    try:
        out = GovernanceEngine(root(), group, project).evaluate(
            raw, role=role, target=target, contract=contract, catalog_columns=cols, write=write,
            approved_action_id=approved)
    except BudgetExceeded as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(3) from exc
    if as_json:
        print(json.dumps(out.to_dict(), indent=2, default=str))
    else:
        colour = {"PASS": "green", "REJECT": "red", "ESCALATED": "yellow", "CIRCUIT_BROKEN": "red"}[out.status.value]
        console.print(f"[{colour}]{out.status.value}[/] {out.target}  action {out.action_id[:12]}…  "
                      f"chain seq {out.chain_seq}")
        for f in out.findings:
            console.print(f"  [{'red' if f.severity == 'error' else 'yellow'}]{f.severity}[/] {f.validator}/{f.code}"
                          f"{' @ ' + f.path if f.path else ''}: {f.message}")
        if out.written:
            console.print(f"  [dim]written: {out.target}[/]")
    raise typer.Exit(EXIT[out.status.value])


@govern_app.command("breaker")
def govern_breaker(group: str, project: str,
                   reset: bool = typer.Option(False, "--reset", help="Write a clean marker to the chain"),
                   reason: str = typer.Option("", "--reason", help="Why, recorded with the reset")) -> None:
    """The circuit breaker's state for an entity, read from the provenance chain."""
    from pf.aidf.breaker import CircuitBreaker
    from pf.aidf.config import load

    cfg = load(root(), group, project)
    br = CircuitBreaker(root(), group, project, cfg.budgets)
    if reset:
        try:
            aid = br.reset(reason)
        except ValueError as exc:
            console.print(f"[red]{exc}[/]")
            raise typer.Exit(1) from exc
        console.print(f"[green]reset[/] recorded as action {aid[:12]}…")
    s = br.state()
    console.print(f"{group}/{project}: {'[red]OPEN[/]' if s.open else '[green]closed[/]'} — "
                  f"{s.consecutive_failures}/{s.limit} consecutive failures{' · ' + s.reason if s.reason else ''}")
    raise typer.Exit(3 if s.open else 0)


@govern_app.command("schema")
def govern_schema(contract: str = typer.Argument("mart_metric")) -> None:
    """The JSON schema an agent's payload must satisfy."""
    from pf.aidf.schemas import CONTRACTS, json_schema

    if contract not in CONTRACTS:
        console.print(f"[red]unknown contract {contract!r}; one of {sorted(CONTRACTS)}[/]")
        raise typer.Exit(1)
    print(json.dumps(json_schema(contract), indent=2, sort_keys=True))


@govern_app.command("prompt")
def govern_prompt(group: str, project: str, mart: str, metric: str,
                  columns: str = typer.Option("", "--columns", help="Override the catalogue")) -> None:
    """The dispatch prompt for a metric sub-agent, with the entity's catalogue and schema."""
    from pf.aidf import catalog
    from pf.aidf.config import load
    from pf.aidf.prompts import metric_prompt

    cfg = load(root(), group, project)
    cols = ({c.strip() for c in columns.split(",") if c.strip()}
            or catalog.columns_for(root() / "groups" / group / "projects" / project, mart) or set())
    print(metric_prompt(group, project, mart, metric, cols, cfg.dialect))


# -------------------------------------------------------------------- dora --
@dora_app.command("matrix")
def dora_matrix(as_json: bool = typer.Option(False, "--json")) -> None:
    """The statutory mapping: which article each automated check evidences."""
    from pf.aidf.dora.mapping import load_mapping

    m = load_mapping()
    if as_json:
        print(json.dumps({"regulation": m.regulation, "articles": [
            {"id": a.id, "title": a.title, "requirement": a.requirement,
             "checks": [{"id": c.id, "kind": c.kind, "description": c.description} for c in a.checks]}
            for a in m.articles]}, indent=2))
        return
    t = Table(box=None, pad_edge=False)
    for col in ("article", "requirement", "check", "evidence"):
        t.add_column(col, overflow="fold")
    for a in m.articles:
        for i, c in enumerate(a.checks):
            t.add_row(f"{a.label} {a.title}" if i == 0 else "", a.requirement if i == 0 else "", c.id,
                      f"[dim]{c.kind}[/] {c.description}")
    console.print(t)
    console.print(f"\n[dim]{len(m.articles)} article(s) · {len(m.checks())} check(s) · {m.regulation}[/]")


@dora_app.command("check")
def dora_check() -> None:
    """The matrix is well-formed and every entity's DORA config resolves. The CI step."""
    from pf.aidf.config import AidfConfigError, entities, load
    from pf.aidf.dora.mapping import PROVIDERS, load_mapping, validate_mapping

    problems = validate_mapping(load_mapping())
    for g, p in entities(root()):
        try:
            cfg = load(root(), g, p)
            for prov in cfg.providers:
                if prov not in PROVIDERS:
                    problems.append(f"{g}/{p}: unknown provider {prov!r} (one of {', '.join(PROVIDERS)})")
        except AidfConfigError as exc:
            problems.append(f"{g}/{p}: {exc}")
    for line in problems:
        console.print(f"[red]✗[/] {line}")
    if not problems:
        console.print("[green]✓[/] matrix well-formed; every entity's DORA config resolves")
    raise typer.Exit(1 if problems else 0)


@dora_app.command("r2")
def dora_r2(
    out: Path = typer.Option(Path(".tmp/dora/prowler_cloudflare_r2.ocsf.json"), "--out",
                             help="Where to write the OCSF findings; feed it to `pf dora audit --ocsf`"),
    account_id: str = typer.Option("", "--account-id",
                                   help="Cloudflare account id; default from env or PF_ARTIFACTS_ENDPOINT"),
) -> None:
    """Judge every R2 bucket in the account — public access, TLS, CORS, lifecycle — as OCSF findings.

    Prowler's cloudflare provider covers zones, DNS and the WAF and has no R2
    checks; the artefact store lives in R2, so this is the platform's own scan.
    Needs CLOUDFLARE_API_TOKEN (or DORA_CLOUDFLARE_API_TOKEN) with
    'Workers R2 Storage: Read'.
    """
    from pf.aidf.dora import r2

    token = r2.token_from_env()
    acct = account_id or r2.account_id_from_env()
    if not token:
        console.print("[red]no CLOUDFLARE_API_TOKEN / DORA_CLOUDFLARE_API_TOKEN in the environment[/]")
        raise typer.Exit(2)
    if not acct:
        console.print("[red]no account id: pass --account-id, set CLOUDFLARE_ACCOUNT_ID, "
                      "or set PF_ARTIFACTS_ENDPOINT[/]")
        raise typer.Exit(2)
    try:
        findings = r2.scan(acct, r2.http_fetch(token))
    except r2.R2AccessError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(1) from exc
    path = r2.write_ocsf(findings, root() / out if not out.is_absolute() else out)
    s = r2.summary(findings)
    console.print(f"[green]{s['buckets']} bucket(s)[/] · {s['pass']} pass · {s['fail']} fail · "
                  f"{s['manual']} manual → {path}")
    raise typer.Exit(1 if s["fail"] else 0)


@dora_app.command("audit")
def dora_audit(
    group: str | None = typer.Argument(None), project: str | None = typer.Argument(None),
    provider: str = typer.Option("", "--provider", help="aws | azure | gcp | kubernetes; overrides aidf.yaml"),
    ocsf: list[Path] | None = typer.Option(None, "--ocsf", help="Prowler OCSF JSON to ingest instead of running "
                                                             "Prowler; repeat for several scans (gcp + github)"),
    vulns: Path | None = typer.Option(None, "--vulns", help="Trivy JSON or CycloneDX with vulnerabilities to ingest"),
    sbom: Path | None = typer.Option(None, "--sbom", help="A CycloneDX SBOM produced elsewhere"),
    out: Path | None = typer.Option(None, "--out", help="Where to write; default <project>/governance/dora"),
    run_tools: bool = typer.Option(True, "--run/--no-run", help="Invoke prowler/trivy when on PATH"),
    live: bool = typer.Option(False, "--live", help="Read repository settings through gh"),
    record: bool = typer.Option(True, "--record/--no-record", help="Record the audit to the provenance chain"),
    as_json: bool = typer.Option(False, "--json"),
    markdown: bool = typer.Option(False, "--markdown", help="Print the matrix as Markdown (for a step summary)"),
) -> None:
    """Run the audit for one entity, one family, or every entity in the checkout."""
    from pf.aidf.dora.audit import run_audit

    entities = _entities(group, project)
    # Aggregate audits share one runtime ledger in this checkout. Recording the
    # first entity would make later entities judge that brand-new audit record as
    # pre-existing provenance, which turns "no anchor here yet" into a false
    # failure. Record only single-entity audits; aggregate CI runs archive the
    # matrices and their scan inputs instead.
    record_each = record and len(entities) == 1
    worst = 0
    for g, p in entities:
        rep = run_audit(root(), g, p, provider=provider or None, ocsf=ocsf or None, vulns=vulns, sbom=sbom,
                        out_dir=out if (out and group and project) else None, run_tools=run_tools, live=live,
                        record=record_each)
        worst = max(worst, rep.exit_code)
        if as_json:
            print(json.dumps(rep.to_dict(), indent=2, sort_keys=True))
        elif markdown:
            print(rep.to_markdown())
        else:
            c = rep.counts()
            colour = {"pass": "green", "fail": "red", "pass_with_gaps": "yellow", "not_applicable": "dim"}[rep.overall]
            console.print(f"[{colour}]{rep.overall.upper()}[/] {g}/{p} — {c['pass']} pass · {c['fail']} fail · "
                          f"{c['unverified']} unverified · {c['not_applicable']} n/a  → {rep.out_dir}/matrix.md")
            for a in rep.articles:
                if a.status in ("fail",):
                    for ch in a.checks:
                        if ch.status == "fail":
                            console.print(f"  [red]✗[/] {a.label} {ch.check_id}: {ch.detail}")
    raise typer.Exit(worst)
