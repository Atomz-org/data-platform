"""OpenMetadata — the catalogue every other layer publishes into.

## Where this sits

The platform already knows what its data *means*: the ontology names the
concepts, the topology names the relations between them, annotations say what
each column is, and the policy layer says what may not happen to it. Every one of
those is projected somewhere already — MDL for the semantic layer, OWL for the
formal one, otop for the evidence chain. OpenMetadata is the projection aimed at
people: the place someone who does not read YAML goes to ask what `fct_revenue`
is and whether it contains personal data.

Nothing here is specific to a project. Everything is derived from the project it
is bootstrapped into — its dbt project, its warehouse, its group's ontology — so
a project scaffolded tomorrow gets the same integration without an edit here.

## The division of labour, which is the whole design

    metadata ingest-dbt   tables, columns, column-level lineage, dbt tests
    this module           what those tables *mean*

`metadata ingest-dbt` reads `manifest.json` / `catalog.json` / `run_results.json`
and does the physical half properly, including lineage we would only be
re-deriving worse from the knowledge graph. Emitting tables from both sides would
give the catalogue two descriptions of one table, drifting apart, and it would
show whichever ran last. So the dbt connector owns physical assets and
`pf.projections.openmetadata` owns the vocabulary laid over them.

## One direction only

The catalogue is written to, never read from. The ontology stays canonical in
YAML under git, judged by `pf check` and the gate — the same decision the
governance layer made when it put owner edits behind an audit row and left the
file authoritative. A catalogue that can silently redefine a concept is a second
source of truth, and then neither side can say what `Customer` means.

## Configuration

`host_port`, `jwt_token` and `service_name` come from `tools.yaml` or the
environment, never from a literal here. The token is a credential: it is read
from `OPENMETADATA_JWT_TOKEN` and is never written into any generated file, which
is why `dbt_project.yml` gets an env-var reference rather than the value.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import yaml

from pf.capabilities import Capability
from pf.tools.spec import DbtBinding, Requirement, Surface, Tool, ToolContext, ToolContribution

DEFAULT_PORT = 8585
WORKFLOW_REL = "catalog/ingestion.yaml"
PAYLOAD_REL = "catalog/openmetadata.json"
ENV_TOKEN = "OPENMETADATA_JWT_TOKEN"
ENV_HOST = "OPENMETADATA_HOST_PORT"


# ------------------------------------------------------------------- paths --
def catalog_dir(project_dir: Path) -> Path:
    return Path(project_dir) / "catalog"


def workflow_path(project_dir: Path) -> Path:
    return Path(project_dir) / WORKFLOW_REL


def payload_path(project_dir: Path) -> Path:
    return Path(project_dir) / PAYLOAD_REL


def dbt_dir(project_dir: Path) -> Path:
    return Path(project_dir) / "transform"


# ------------------------------------------------------------------ config --
def settings(config: dict[str, Any] | None, group: str = "",
             project: str = "") -> dict[str, str]:
    """Resolve connection settings: tools.yaml first, then environment, then a default.

    The service name defaults to `<group>_<project>` rather than to the project
    alone. Sister companies have identically named marts by design — that is what
    conformed dimensions mean — and a catalogue keyed on the project name would
    collapse `acme_us.fct_revenue` and `acme_eu.fct_revenue` into one entry.
    """
    cfg = config or {}
    host = str(cfg.get("host_port") or os.environ.get(ENV_HOST) or "http://localhost:8585")
    service = str(cfg.get("service_name") or
                  (f"{group}_{project}".strip("_") if (group or project) else "platform"))
    return {
        "host_port": host.rstrip("/"),
        "service_name": service.replace("-", "_"),
        "auth_provider": str(cfg.get("auth_provider") or "openmetadata"),
    }


def token() -> str:
    """The JWT, from the environment only.

    Never read from `tools.yaml`: that file is committed, and a credential in it
    is a credential in the repository. Absence is reported by `readiness`, not
    raised, so a machine without the token still bootstraps.
    """
    return os.environ.get(ENV_TOKEN, "")


# ------------------------------------------------------------------- probe --
def probe_engine() -> dict[str, Any]:
    """Is the `metadata` CLI usable? Installed and usable are not the same claim."""
    try:
        proc = subprocess.run(["metadata", "--version"], capture_output=True,
                              text=True, timeout=30)
    except FileNotFoundError:
        return {"ok": False, "detail": "metadata CLI not on PATH — `uv tool install openmetadata-ingestion`"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "detail": "metadata --version timed out"}
    if proc.returncode != 0:
        return {"ok": False, "detail": (proc.stderr or proc.stdout or "")[-160:]}
    if not token():
        # Installed, and cannot authenticate. Reported as a blocker rather than
        # a green tick, for the same reason the wren probe exists.
        return {"ok": False, "detail": f"{ENV_TOKEN} is not set — ingestion would be rejected"}
    return {"ok": True, "detail": (proc.stdout or "").strip()[:80] or "metadata CLI ready"}


# ------------------------------------------------------------- projection --
def build_payload(project_dir: Path, group: str, project: str) -> dict[str, Any]:
    """The vocabulary this project publishes: glossary, tags, metrics.

    Metrics are read from the project's own graph when it has one, so a project
    with no models publishes an ontology and no metrics rather than failing.
    """
    from pf.ontology.model import load_ontology
    from pf.projections.openmetadata import build_all

    metrics: list[dict[str, Any]] = []
    graph = Path(project_dir) / "kg" / "graph.json"
    if graph.exists():
        try:
            nodes = json.loads(graph.read_text()).get("nodes") or []
            metrics = [
                {"name": n.get("name") or n.get("id", ""),
                 "description": (n.get("props") or {}).get("description", ""),
                 "expression": (n.get("props") or {}).get("expression", "")}
                for n in nodes if n.get("kind") == "Metric"
            ]
        except (json.JSONDecodeError, AttributeError):
            metrics = []

    payload = build_all(load_ontology(), metrics=metrics)
    payload["service_name"] = settings(None, group, project)["service_name"]
    return payload


# -------------------------------------------------------------- ingestion --
def build_workflow(project_dir: Path, group: str, project: str,
                   config: dict[str, Any] | None = None) -> dict[str, Any]:
    """The dbt ingestion workflow, as OpenMetadata's own schema expects it.

    `dbtConfigSource` points at the artefacts dbt already writes — this platform
    does not copy them anywhere, because a second copy is a second thing that can
    be stale.

    Paths are **relative to the project directory**, and `ingest_dbt` runs the
    CLI with that as its working directory. An absolute path would bake one
    developer's home directory into a committed file, which works on exactly one
    machine and fails in CI — the same fault this platform already carries in
    `mdl/connection.json`, and not one worth repeating.

    The token is written as an env-var reference, not a value, for the same
    reason: this file is generated into a project directory that is committed.
    """
    s = settings(config, group, project)
    target = Path("transform") / "target"
    return {
        "source": {
            "type": "dbt",
            "serviceName": s["service_name"],
            "sourceConfig": {
                "config": {
                    "type": "DBT",
                    "dbtConfigSource": {
                        "dbtConfigType": "local",
                        "dbtManifestFilePath": str(target / "manifest.json"),
                        "dbtCatalogFilePath": str(target / "catalog.json"),
                        "dbtRunResultsFilePath": str(target / "run_results.json"),
                    },
                    # Descriptions and tags are ours: the ontology is the reason
                    # a column is called personal data, so dbt must not overwrite
                    # what the glossary sync publishes.
                    "dbtUpdateDescriptions": False,
                    "dbtUpdateOwners": True,
                    "includeTags": True,
                },
            },
        },
        "sink": {"type": "metadata-rest", "config": {}},
        "workflowConfig": {
            "openMetadataServerConfig": {
                "hostPort": f"{s['host_port']}/api",
                "authProvider": s["auth_provider"],
                "securityConfig": {"jwtToken": f"${{{ENV_TOKEN}}}"},
            },
        },
    }


def write_workflow(project_dir: Path, group: str, project: str,
                   config: dict[str, Any] | None = None) -> tuple[Path, bool]:
    """Write the ingestion workflow if it would change. Returns (path, changed)."""
    body = yaml.safe_dump(build_workflow(project_dir, group, project, config),
                          sort_keys=False)
    header = (
        "# GENERATED by `pf bootstrap` (pf.tools.openmetadata). Do not hand-edit:\n"
        "# it is rewritten from tools.yaml and the project's dbt artefacts.\n"
        f"# The JWT is an env-var reference — set {ENV_TOKEN} where this runs.\n")
    path = workflow_path(project_dir)
    text = header + body
    if path.exists() and path.read_text() == text:
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path, True


def write_payload(project_dir: Path, group: str, project: str) -> tuple[Path, bool]:
    """Write the projected vocabulary. Returns (path, changed)."""
    text = json.dumps(build_payload(Path(project_dir), group, project),
                      indent=2, sort_keys=True) + "\n"
    path = payload_path(project_dir)
    if path.exists() and path.read_text() == text:
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path, True


def ingest_dbt(project_dir: Path, timeout: int = 900) -> dict[str, Any]:
    """Run the dbt ingestion workflow. Never raises — a failure is a result."""
    wf = workflow_path(project_dir)
    if not wf.exists():
        return {"ok": False, "reason": "no_workflow", "message": "run `pf bootstrap`"}
    if not token():
        return {"ok": False, "reason": "no_token",
                "message": f"{ENV_TOKEN} is not set"}
    try:
        # cwd is the project: the workflow's artefact paths are relative to it.
        proc = subprocess.run(["metadata", "ingest", "-c", str(wf.resolve())],
                              cwd=str(Path(project_dir).resolve()),
                              capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return {"ok": False, "reason": "not_installed",
                "message": "metadata CLI not on PATH — `uv tool install openmetadata-ingestion`"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "timeout", "message": "ingestion timed out"}
    return {"ok": proc.returncode == 0,
            "reason": "" if proc.returncode == 0 else "ingest_failed",
            "message": (proc.stderr or proc.stdout or "")[-2000:]}


def recce_test_cases(project_dir: Path, service_name: str) -> list[dict[str, Any]]:
    """Recce's recorded checks as OpenMetadata test cases.

    Review findings belong in the catalogue: "this table's plan_tier drifted" is
    exactly what someone browsing `fct_revenue` needs to know, and it is
    otherwise only visible to whoever opened the review.

    `testPlatform` is `Other`, not `dbt`. These are not dbt tests — they are
    diffs recce computed against a captured baseline — and claiming a platform
    that did not produce them would misattribute the result.
    """
    try:
        from pf.tools.recce import check_results
    except ImportError:  # recce not installed; nothing to publish
        return []

    cases: list[dict[str, Any]] = []
    for c in check_results(Path(project_dir)):
        model = c.get("model") or ""
        if not model:
            # A check with no model has nowhere to hang in the catalogue.
            continue
        cases.append({
            "name": c["name"].replace("::", "_")[:256],
            "description": c.get("description", ""),
            "entityLink": f"<#E::table::{service_name}.{model}>",
            "testDefinition": "tableRowCountToBeBetween"
            if c["type"] == "row_count_diff" else "tableCustomSQLQuery",
            "_verdict": c["verdict"],
            "_detail": c.get("detail", ""),
        })
    return cases


# --------------------------------------------------------------- bootstrap --
def bootstrap_project(root: Path, group: str, project: str,
                      project_dir: Path, config: dict[str, Any]) -> Any:
    """Idempotent per-project setup. Runs on every `pf bootstrap`.

    Writes the workflow and the projected vocabulary. Deliberately does *not*
    contact the server: bootstrap must succeed on a laptop with no catalogue
    running, and an integration that only works when a service is up is one that
    breaks scaffolding for everyone else.
    """
    from pf.scaffold.bootstrap import StepResult

    d = Path(project_dir)
    if not (dbt_dir(d) / "dbt_project.yml").exists():
        return StepResult("openmetadata", "skipped", "no dbt project")

    _, wf_changed = write_workflow(d, group, project, config)
    _, pl_changed = write_payload(d, group, project)
    payload = build_payload(d, group, project)

    detail = (f"{len(payload['glossary_terms'])} term(s), "
              f"{len(payload['tags'])} tag(s)")
    if not (wf_changed or pl_changed):
        detail += ", unchanged"
    probe = probe_engine()
    if not probe["ok"]:
        detail += f" · not ingested ({probe['detail'][:60]})"
    return StepResult("openmetadata", "ok", detail)


# ----------------------------------------------------------------- dagster --
def dagster_assets(ctx: ToolContext) -> ToolContribution:
    """Publish to the catalogue after the marts are built, not on a timer.

    Downstream of this project's models, so the catalogue describes the build
    that just happened. A scheduled catalogue job drifts from the warehouse
    between runs and nobody can tell which state they are looking at.
    """
    from dagster import AssetKey, MetadataValue, asset

    project_dir = Path(ctx.project_dir)
    prefix = ctx.project.replace("-", "_")
    s = settings(ctx.config, ctx.group, ctx.project)

    @asset(
        name="openmetadata_catalog",
        key_prefix=[prefix],
        group_name="catalog",
        description="Publish this project's vocabulary and dbt metadata to OpenMetadata.",
        compute_kind="openmetadata",
    )
    def _catalog(context) -> None:  # noqa: ANN001 — see dagster_runtime note
        write_workflow(project_dir, ctx.group, ctx.project, ctx.config)
        write_payload(project_dir, ctx.group, ctx.project)
        payload = build_payload(project_dir, ctx.group, ctx.project)
        result = ingest_dbt(project_dir)
        cases = recce_test_cases(project_dir, s["service_name"])

        context.add_output_metadata({
            "service": MetadataValue.text(s["service_name"]),
            "glossary_terms": MetadataValue.int(len(payload["glossary_terms"])),
            "tags": MetadataValue.int(len(payload["tags"])),
            "metrics": MetadataValue.int(len(payload["metrics"])),
            "review_findings": MetadataValue.int(
                sum(1 for c in cases if c.get("_verdict") == "changed")),
            "ingested": MetadataValue.bool(bool(result.get("ok"))),
            # The reason, not just the boolean. "ingested: false" with no cause
            # sends whoever is on call to read logs this asset already has.
            "detail": MetadataValue.text(
                str(result.get("message") or result.get("reason") or "ok")[:900]),
            "workflow": MetadataValue.path(str(workflow_path(project_dir))),
        })

    return ToolContribution(assets=[_catalog])


# ------------------------------------------------------------- capability --
DOCS = """\
# OpenMetadata — the catalogue for {{group}}/{{project}}

The catalogue is where someone who does not read YAML finds out what a table
means. This project publishes into it automatically.

```bash
pf tool openmetadata payload {{group}} {{project}}   # what would be published
pf tool openmetadata sync {{group}} {{project}}      # regenerate the artefacts
pf tool openmetadata ingest {{group}} {{project}}    # run the dbt ingestion
pf tool doctor {{group}} {{project}}                 # can it actually reach the server
```

## What publishes what

| Source | Becomes |
|---|---|
| `platform/.../concepts.yaml` | Glossary terms, with identity and properties |
| ontology roles | `PlatformRole` tags; PII roles also get `PII.Sensitive` |
| topology relations | `relatedTerms` between glossary terms |
| policy layer | Glossary terms describing each constraint |
| dbt `target/*.json` | Tables, columns and column-level lineage |
| recce checks | Test cases carrying the review verdict |

Tables and lineage come from `metadata ingest-dbt`, not from us. We publish what
they *mean*; dbt publishes what they *are*.

## It is a projection, not a sync

Nothing is read back. Edit `concepts.yaml` and re-run — a change made in the
catalogue UI is overwritten on the next publish, on purpose. The ontology is
canonical and stays in git where `pf check` and the gate can judge it.

## Configuration

`OPENMETADATA_JWT_TOKEN` must be set wherever ingestion runs; it is a credential
and is never written into a generated file. Host and service name come from
`tools.yaml`, defaulting to `http://localhost:8585` and `{{group}}_{{project}}`.
"""

CAPABILITY = Capability(
    name="openmetadata",
    description="Publish the ontology, dbt metadata and review findings to OpenMetadata.",
    files={"docs/openmetadata.md": DOCS},
    settings={"permissions": {"allow": [
        "Bash(pf tool openmetadata:*)", "Bash(metadata:*)",
    ]}},
    gate={
        # Both are projections of things that live elsewhere. Editing either
        # forks the catalogue from the ontology it claims to publish.
        "denylist": [f"**/{WORKFLOW_REL}", f"**/{PAYLOAD_REL}"],
    },
)

TOOL = Tool(
    name="openmetadata",
    title="OpenMetadata",
    summary="Catalogue: publish the ontology, dbt lineage and review findings.",
    url="https://github.com/open-metadata/OpenMetadata",
    scope=frozenset({"project", "group"}),
    capability=CAPABILITY,
    default_enabled=True,
    # The projection needs no client; only ingestion does. See spec.Tool.
    offline_bootstrap=True,
    # Binary only. There was a `python:metadata` requirement beside this one,
    # and it was never true of anything: this module shells out to `metadata
    # ingest` and does not import a line of the package. Now that ingestion is
    # installed isolated — because its antlr4 pin was breaking Dagster, see the
    # note in the root pyproject.toml — an import check would be permanently
    # unsatisfiable, and would report a correctly installed tool as missing.
    requires=(
        Requirement("binary", "metadata",
                    "uv tool install 'openmetadata-ingestion[datalake,snowflake]'"),
    ),
    dbt=DbtBinding(needs_manifest=True, artefacts=(WORKFLOW_REL, PAYLOAD_REL)),
    # Not embeddable: OpenMetadata serves its UI with a frame-denying policy, so
    # an iframe would render a blank rectangle the operator is left to debug.
    # Deep-linked instead, which is what `Surface.embeddable` exists to express.
    surface=Surface(port=DEFAULT_PORT, path="/", embeddable=False),
    health="pf.tools.openmetadata:probe_engine",
    bootstrap="pf.tools.openmetadata:bootstrap_project",
    dagster="pf.tools.openmetadata:dagster_assets",
    commands="pf.tools.openmetadata:register_commands",
    stack_layer={
        "layer": "catalog", "title": "Catalogue (OpenMetadata)",
        "upstream": "openmetadata", "toolkits": [],
        "artefacts": PAYLOAD_REL, "node_kinds": ["Concept", "Metric"],
    },
)


# -------------------------------------------------------------------- cli --
def register_commands(app: Any) -> None:
    """Attach `pf tool openmetadata ...`. Imported lazily by the CLI."""
    import typer
    from rich.console import Console
    from rich.table import Table as RichTable

    console = Console()
    om = typer.Typer(help="OpenMetadata: publish the ontology and dbt metadata.")

    def _pdir(group: str, project: str) -> Path:
        from pf.cli import pdir
        return pdir(group, project)

    @om.command("payload")
    def cmd_payload(group: str, project: str) -> None:
        """What would be published, without contacting the server."""
        p = build_payload(_pdir(group, project), group, project)
        t = RichTable("entity", "count")
        t.add_row("glossary terms", str(len(p["glossary_terms"])))
        t.add_row("role tags", str(len(p["tags"])))
        t.add_row("metrics", str(len(p["metrics"])))
        console.print(t)

    @om.command("sync")
    def cmd_sync(group: str, project: str) -> None:
        """Regenerate the workflow and the projected vocabulary."""
        d = _pdir(group, project)
        wf, wf_changed = write_workflow(d, group, project, None)
        pl, pl_changed = write_payload(d, group, project)
        for path, changed in ((wf, wf_changed), (pl, pl_changed)):
            console.print(f"  {'[green]wrote[/]' if changed else '[dim]unchanged[/]'} {path}")

    @om.command("ingest")
    def cmd_ingest(group: str, project: str) -> None:
        """Run the dbt ingestion workflow against the configured server."""
        r = ingest_dbt(_pdir(group, project))
        console.print(("[green]✓[/] ingested" if r["ok"]
                       else f"[red]✗[/] {r.get('reason')}: {r.get('message', '')[:400]}"))
        if not r["ok"]:
            raise typer.Exit(1)

    app.add_typer(om, name="openmetadata")
