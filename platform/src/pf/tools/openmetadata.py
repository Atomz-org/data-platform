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

## One direction, plus a proposal channel

The catalogue is written to, never read from *automatically*. The ontology stays
canonical in YAML under git, judged by `pf check` and the gate — the same
decision the governance layer made when it put owner edits behind an audit row
and left the file authoritative. A catalogue that can silently redefine a
concept is a second source of truth, and then neither side can say what
`Customer` means.

But a catalogue nobody may write to is a catalogue nobody uses. A data owner who
finds `paid_at` documented wrongly needs somewhere to put the correction, and
"open a YAML file in a monorepo" is not that place for most of the people who
know the answer.

So `pull` is the seam: it reads back descriptions, owners and tags, diffs them
against what this project published, and writes the differences to
`catalog/owner-edits.yaml` — a **proposal**, not an application. Nothing under
`contracts/` moves until a human puts the change in a pull request, where it
gets the same review as any other change to what a column means. The catalogue
gains an edit path; git keeps the last word.

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

#: Ingestion workflows, in the order they must run.
#:
#: `database` is not optional and used to be missing, which made the rest of
#: this tool decorative. OpenMetadata's dbt ingestion is an *enrichment* pass:
#: it attaches models, lineage, tests and owners to tables that a database
#: service has already catalogued. With no database service there is nothing to
#: attach to, so a project published its glossary, its tags and its metrics into
#: a catalogue containing not one table — and a data owner opening it saw a
#: vocabulary with nothing underneath.
#:
#: Order is the dependency: tables, then everything said about them.
INGESTION_DIR = "catalog/ingestion"
WORKFLOWS: tuple[str, ...] = ("database", "dbt")


# ------------------------------------------------------------------- paths --
def catalog_dir(project_dir: Path) -> Path:
    return Path(project_dir) / "catalog"


def ingestion_dir(project_dir: Path) -> Path:
    return Path(project_dir) / INGESTION_DIR


def ingestion_path(project_dir: Path, name: str) -> Path:
    return ingestion_dir(project_dir) / f"{name}.yaml"


def workflow_path(project_dir: Path) -> Path:
    """The dbt workflow's path.

    Kept pointing at the new location rather than the old single file, so every
    existing caller — the Dagster asset, `pf tool doctor` — follows the move
    without an edit.
    """
    return ingestion_path(project_dir, "dbt")


def legacy_workflow_path(project_dir: Path) -> Path:
    """`catalog/ingestion.yaml`, from when there was only one workflow.

    Removed rather than left behind: it is a valid dbt workflow, so anyone who
    ran it would enrich a catalogue that no longer has a database pass in front
    of it and get the empty result this split exists to fix.
    """
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
            nodes = json.loads(graph.read_text(encoding="utf-8")).get("nodes") or []
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
def _server_config(s: dict[str, str]) -> dict[str, Any]:
    """The `workflowConfig` block every workflow ends with.

    The token is an env-var *reference*, never a value: these files are
    generated into a project directory that is committed.
    """
    return {
        "openMetadataServerConfig": {
            "hostPort": f"{s['host_port']}/api",
            "authProvider": s["auth_provider"],
            "securityConfig": {"jwtToken": f"${{{ENV_TOKEN}}}"},
        },
    }


def build_database_workflow(project_dir: Path, group: str, project: str,
                            config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Catalogue the production warehouse's schemas, tables and columns.

    This is the pass that puts *tables* in the catalogue. Everything else this
    tool writes — the glossary, the role tags, the metrics, the dbt lineage, the
    recce test cases — describes tables, and none of it has anywhere to land
    until this has run.

    It points at **production**, not at a developer's DuckDB file, and the
    connection comes from `pf.runtime.targets` so the engine the platform
    deploys to and the engine it catalogues cannot disagree. Switching a project
    to BigQuery moves both.

    Returns `{}` when the production warehouse declares no OpenMetadata
    connection, which `write_workflows` reports rather than writing a workflow
    that would fail at run time.
    """
    from pf.runtime.targets import default_warehouse

    s = settings(config, group, project)
    wh = default_warehouse()
    if wh is None or not wh.om_connection:
        return {}

    return {
        "source": {
            "type": wh.om_type.lower(),
            "serviceName": s["service_name"],
            "serviceConnection": {"config": dict(wh.om_connection)},
            "sourceConfig": {
                "config": {
                    "type": "DatabaseMetadata",
                    # Marts are what a data owner opens the catalogue to read.
                    # Everything else is included too — a lineage graph that
                    # stops at the staging boundary cannot answer "where did
                    # this number come from", which is the question being asked.
                    "includeTables": True,
                    "includeViews": True,
                    "markDeletedTables": True,
                },
            },
        },
        "sink": {"type": "metadata-rest", "config": {}},
        "workflowConfig": _server_config(s),
    }


def build_workflow(project_dir: Path, group: str, project: str,
                   config: dict[str, Any] | None = None) -> dict[str, Any]:
    """The dbt ingestion workflow, as OpenMetadata's own schema expects it.

    `dbtConfigSource` points at the artefacts dbt already writes — this platform
    does not copy them anywhere, because a second copy is a second thing that can
    be stale.

    Paths are **relative to the project directory**, and `ingest` runs the
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
        "workflowConfig": _server_config(s),
    }


def build_workflows(project_dir: Path, group: str, project: str,
                    config: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """Every ingestion workflow, keyed by name, in run order.

    A workflow that cannot be built is omitted rather than emitted empty — the
    caller reports the gap, and `metadata ingest` is never handed a file that
    was always going to fail.
    """
    built = {
        "database": build_database_workflow(project_dir, group, project, config),
        "dbt": build_workflow(project_dir, group, project, config),
    }
    return {name: built[name] for name in WORKFLOWS if built.get(name)}


def write_workflows(project_dir: Path, group: str, project: str,
                    config: dict[str, Any] | None = None) -> tuple[list[Path], list[str]]:
    """Write every ingestion workflow. Returns (paths written, names that changed).

    Also removes `catalog/ingestion.yaml`, the single file this replaced. Left
    in place it is a runnable dbt workflow with no database pass in front of it,
    which produces exactly the empty catalogue the split exists to fix — a stale
    file that still works is more dangerous than one that errors.
    """
    header = (
        "# GENERATED by `pf bootstrap` (pf.tools.openmetadata). Do not hand-edit:\n"
        "# it is rewritten from tools.yaml, pf.runtime.targets and the project's\n"
        "# dbt artefacts.\n"
        f"# Credentials are env-var references — set {ENV_TOKEN} and the\n"
        "# warehouse's own variables where this runs. No secret is in this file.\n")

    written: list[Path] = []
    changed: list[str] = []
    for name, workflow in build_workflows(project_dir, group, project, config).items():
        text = header + yaml.safe_dump(workflow, sort_keys=False)
        path = ingestion_path(project_dir, name)
        written.append(path)
        if path.exists() and path.read_text(encoding="utf-8") == text:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        changed.append(name)

    legacy = legacy_workflow_path(project_dir)
    if legacy.exists():
        legacy.unlink()
        changed.append("-ingestion.yaml")
    return written, changed


def write_workflow(project_dir: Path, group: str, project: str,
                   config: dict[str, Any] | None = None) -> tuple[Path, bool]:
    """The dbt workflow alone. Kept for callers that only want that one."""
    _, changed = write_workflows(project_dir, group, project, config)
    return workflow_path(project_dir), "dbt" in changed


def write_payload(project_dir: Path, group: str, project: str) -> tuple[Path, bool]:
    """Write the projected vocabulary. Returns (path, changed)."""
    text = json.dumps(build_payload(Path(project_dir), group, project),
                      indent=2, sort_keys=True) + "\n"
    path = payload_path(project_dir)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path, True


def ingest(project_dir: Path, only: str = "", timeout: int = 900) -> list[dict[str, Any]]:
    """Run every ingestion workflow, in order. One result per workflow.

    Stops at the first failure. The order is a dependency, not a preference —
    dbt enrichment attaches to tables the database pass catalogued — so running
    dbt after a failed database pass would report a second, more confusing
    error about a service that does not exist.
    """
    results: list[dict[str, Any]] = []
    for name in WORKFLOWS:
        if only and name != only:
            continue
        path = ingestion_path(project_dir, name)
        if not path.exists():
            continue
        r = _ingest_one(path, project_dir, timeout)
        r["workflow"] = name
        results.append(r)
        if not r["ok"]:
            break
    if not results:
        return [{"ok": False, "reason": "no_workflow", "workflow": only or "?",
                 "message": "no ingestion workflow written — run `pf bootstrap`"}]
    return results


def _ingest_one(wf: Path, project_dir: Path, timeout: int) -> dict[str, Any]:
    """Run one workflow. Never raises — a failure is a result."""
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


# ------------------------------------------------------------- publish --
#: PUT endpoint per payload section, in dependency order.
#:
#: Order is not cosmetic. A tag cannot be created before the classification it
#: belongs to, and a glossary term cannot be created before its glossary — the
#: server rejects both with a 404 on the parent, which reads like a bad URL.
PUBLISH_ORDER: tuple[tuple[str, str, bool], ...] = (
    # (payload key, API path, is_list)
    ("classification", "classifications", False),
    ("tags", "tags", True),
    ("glossary", "glossaries", False),
    ("glossary_terms", "glossaryTerms", True),
    ("metrics", "metrics", True),
)


def publish_payload(project_dir: Path, group: str, project: str,
                    config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Send the projected vocabulary to OpenMetadata.

    This is the half that was missing. `build_payload` has always produced a
    correct, API-shaped glossary — terms, role tags, the classification, the
    metrics — and `write_payload` has always written it to
    `catalog/openmetadata.json`. Nothing ever sent it. The tool's own docs said
    "This project publishes into it automatically" and `payload` was described
    as "what *would* be published", which was accurate in a way nobody noticed:
    there was no publisher. A catalogue that had ingested every table still had
    none of this platform's vocabulary laid over it.

    Deliberately independent of the ingestion workflows. The vocabulary
    describes concepts, not tables, so it needs no database service and no
    warehouse credentials — which means it publishes on a laptop against a local
    OpenMetadata, and it publishes even when the production warehouse is
    unreachable. Those are the two situations someone actually wants to see the
    glossary in.

    PUT, not POST: OpenMetadata's PUT is create-or-update for these entities, so
    re-publishing an unchanged ontology is a no-op rather than a conflict. That
    is what makes this safe to run from a bootstrap hook.
    """
    s = settings(config, group, project)
    payload = build_payload(Path(project_dir), group, project)
    result: dict[str, Any] = {"ok": True, "host": s["host_port"], "sent": {},
                              "failed": []}

    for key, path, is_list in PUBLISH_ORDER:
        items = payload.get(key)
        if not items:
            continue
        rows = items if is_list else [items]
        ok = 0

        # Glossary terms are written twice: once bare, then again with their
        # `relatedTerms`. A related term is a reference to another term by FQN,
        # and the server 404s if that term does not exist yet — so *any* single
        # ordering fails as soon as the ontology has a cycle, and an ontology
        # that relates Customer to Order and Order to Customer has one by
        # design. Creating the nodes first and the edges second is the only
        # ordering that always works, and it costs one extra PUT per term.
        deferred: list[dict[str, Any]] = []
        for row in rows:
            body = dict(row)
            if key == "glossary_terms":
                body.setdefault("glossary", payload["glossary"]["name"])
                if body.get("relatedTerms"):
                    deferred.append(dict(body))
                    body.pop("relatedTerms", None)
            try:
                _api_write(s["host_port"], path, body)
                ok += 1
            except RuntimeError as exc:
                result["failed"].append(f"{key}/{row.get('name', '?')}: {exc}")

        for body in deferred:
            try:
                _api_write(s["host_port"], path, body)
            except RuntimeError as exc:
                # The term itself is already published; only its edges are
                # missing, so this degrades the graph rather than losing a
                # definition. Reported separately so that distinction survives.
                result["failed"].append(
                    f"{key}/{body.get('name', '?')} relatedTerms: {exc}")
        result["sent"][key] = ok

    result["ok"] = not result["failed"]
    return result


def _api_write(host_port: str, path: str, body: dict[str, Any],
               timeout: int = 60) -> Any:
    """One authenticated PUT against the OpenMetadata API."""
    import urllib.error
    import urllib.request

    jwt = token()
    if not jwt:
        raise RuntimeError(f"{ENV_TOKEN} is not set")
    req = urllib.request.Request(
        f"{host_port}/api/v1/{path.lstrip('/')}",
        data=json.dumps(body).encode(),
        method="PUT",
        headers={"Authorization": f"Bearer {jwt}",
                 "Content-Type": "application/json",
                 "Accept": "application/json"},
    )
    try:
        # Fixed scheme, operator-configured host; not user input.
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: "
                           f"{exc.read()[:200].decode(errors='replace')}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"cannot reach {host_port}: {exc}") from exc


# -------------------------------------------------------------- tables --
def column_roles(project_dir: Path) -> dict[str, str]:
    """column name -> ontology role, from `contracts/annotations.yaml`.

    Renames are followed: a column annotated as `created` and renamed to
    `paid_at` is catalogued under `paid_at`, because that is what the warehouse
    holds and what a data owner will search for.
    """
    p = Path(project_dir) / "contracts" / "annotations.yaml"
    if not p.exists():
        return {}
    try:
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}
    out: dict[str, str] = {}
    for res in doc.get("resources") or []:
        if not isinstance(res, dict):
            continue
        for col, role in (res.get("roles") or {}).items():
            out[str(col)] = str(role)
        for src, dst in (res.get("rename") or {}).items():
            if str(src) in out:
                out[str(dst)] = out[str(src)]
    return out


def publish_tables(project_dir: Path, group: str, project: str,
                   config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create the service, database, schemas and tables in OpenMetadata.

    The projection is pure and lives in `pf.projections.openmetadata`; this is
    only the HTTP half. See that module for why tables are emitted here at all,
    given the dbt connector exists.

    Order is a dependency chain the server enforces — service, database, schema,
    then tables — and each is a PUT, so re-running after an unchanged build is a
    no-op rather than a conflict.
    """
    from pf.projections.openmetadata import build_database_entities
    from pf.runtime.dbt_runtime import manifest as load_manifest

    d = Path(project_dir)
    man = load_manifest(d)
    if not man:
        return {"ok": False, "reason": "no_manifest",
                "message": "no dbt manifest — run `pf seed` first"}
    cat_path = dbt_dir(d) / "target" / "catalog.json"
    catalog = json.loads(cat_path.read_text(encoding="utf-8")) if cat_path.exists() else {}

    s = settings(config, group, project)
    built = build_database_entities(
        man, catalog,
        service=s["service_name"],
        fallback_database=project.replace("-", "_"),
        column_roles=column_roles(d),
        column_tag_labels=build_payload(d, group, project).get("column_tag_labels"),
    )

    host, service, database = s["host_port"], built["service"], built["database"]
    _api_write(host, "services/databaseServices", {
        "name": service, "serviceType": "CustomDatabase",
        "description": f"{group}/{project} — projected from its dbt manifest by "
                       "`pf.projections.openmetadata`. Metadata is pushed, not "
                       "crawled; this service holds no live connection.",
        "connection": {"config": {"type": "CustomDatabase",
                                  "sourcePythonClass": "pf.projections.openmetadata"}},
    })
    _api_write(host, "databases", {"name": database, "service": service})
    for schema in built["schemas"]:
        _api_write(host, "databaseSchemas",
                   {"name": schema, "database": f"{service}.{database}"})

    ok, skipped, failed = 0, 0, []
    for table in built["tables"]:
        # A parsed-but-never-built model has no columns and the API rejects it.
        # Skipped and counted rather than failed: it is a true statement about
        # the project, and inventing a placeholder column would put a fiction in
        # the catalogue.
        if not table["columns"]:
            skipped += 1
            continue
        try:
            _api_write(host, "tables", table)
            ok += 1
        except RuntimeError as exc:
            failed.append(f"{table['name']}: {exc}")

    return {"ok": not failed, "service": service, "database": database,
            "schemas": len(built["schemas"]), "tables": ok, "skipped": skipped,
            "failed": failed}


# ----------------------------------------------------------- owner edits --
EDITS_REL = "catalog/owner-edits.yaml"


def edits_path(project_dir: Path) -> Path:
    return Path(project_dir) / EDITS_REL


def _api(host_port: str, path: str, timeout: int = 60) -> Any:
    """One authenticated GET against the OpenMetadata API.

    urllib rather than a client library: this is three GETs, and adding an
    `openmetadata-ingestion` import to the platform environment is exactly the
    dependency that was just removed for pinning antlr4 and breaking Dagster.
    """
    import urllib.error
    import urllib.request

    jwt = token()
    if not jwt:
        raise RuntimeError(f"{ENV_TOKEN} is not set")
    req = urllib.request.Request(
        f"{host_port}/api/v1/{path.lstrip('/')}",
        headers={"Authorization": f"Bearer {jwt}", "Accept": "application/json"},
    )
    try:
        # Fixed scheme, operator-configured host; not user input.
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} on /{path}: "
                           f"{exc.read()[:300].decode(errors='replace')}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"cannot reach {host_port}: {exc}") from exc


def fetch_tables(host_port: str, service_name: str, limit: int = 1000) -> list[dict[str, Any]]:
    """Every table the catalogue holds for this project's service, with its columns."""
    out: list[dict[str, Any]] = []
    after = ""
    while True:
        q = (f"tables?service={service_name}&fields=owners,tags,columns"
             f"&limit={min(limit, 100)}" + (f"&after={after}" if after else ""))
        page = _api(host_port, q)
        out.extend(page.get("data") or [])
        after = ((page.get("paging") or {}).get("after")) or ""
        if not after or len(out) >= limit:
            break
    return out


def _published_descriptions(project_dir: Path) -> dict[str, str]:
    """What this project *said* a column means, keyed by column name.

    From `contracts/annotations.yaml`, which is the file a proposal would end up
    editing — so the diff is against the thing that would change, not against
    some other projection of it.
    """
    p = Path(project_dir) / "contracts" / "annotations.yaml"
    if not p.exists():
        return {}
    try:
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}
    out: dict[str, str] = {}
    for res in doc.get("resources") or []:
        if not isinstance(res, dict):
            continue
        name = str(res.get("resource") or "")
        if name and res.get("description"):
            out[name] = str(res["description"])
    return out


def pull_edits(project_dir: Path, group: str, project: str,
               config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Read owner edits out of the catalogue. Never writes under `contracts/`.

    Returns a structure describing what a data owner changed in OpenMetadata
    that this repository does not yet say. Applying it is a human's decision and
    a pull request — see the module docstring on why the YAML keeps the last
    word.
    """
    s = settings(config, group, project)
    try:
        tables = fetch_tables(s["host_port"], s["service_name"])
    except RuntimeError as exc:
        return {"ok": False, "reason": "unreachable", "message": str(exc)}

    published = _published_descriptions(Path(project_dir))
    proposals: list[dict[str, Any]] = []
    for t in tables:
        name = str(t.get("name") or "")
        entry: dict[str, Any] = {}

        # A description the catalogue has and we do not, or one that differs.
        desc = (t.get("description") or "").strip()
        if desc and desc != (published.get(name) or "").strip():
            entry["description"] = desc

        owners = [o.get("name") or o.get("displayName") or ""
                  for o in (t.get("owners") or []) if isinstance(o, dict)]
        if owners:
            entry["owners"] = [o for o in owners if o]

        cols = {}
        for c in t.get("columns") or []:
            cd = (c.get("description") or "").strip()
            if cd:
                cols[str(c.get("name") or "")] = cd
        if cols:
            entry["columns"] = cols

        if entry:
            entry["table"] = name
            proposals.append(entry)

    return {"ok": True, "service": s["service_name"], "tables": len(tables),
            "proposals": proposals}


def write_edits(project_dir: Path, result: dict[str, Any]) -> tuple[Path, bool]:
    """Write the proposal file. Returns (path, changed)."""
    header = (
        "# Edits made by data owners in OpenMetadata that this repository does\n"
        "# not yet reflect. GENERATED by `pf tool openmetadata pull` — a\n"
        "# *proposal*, not applied config.\n"
        "#\n"
        "# Nothing here takes effect. `contracts/annotations.yaml` is canonical\n"
        "# and is what `pf check` and the gate judge; move a line across by hand,\n"
        "# in a pull request, so a change to what a column means gets the review\n"
        "# any other such change gets.\n"
        "#\n"
        "# Empty proposals means the catalogue and this repository agree.\n")
    body = yaml.safe_dump(
        {"service": result.get("service", ""),
         "tables_seen": result.get("tables", 0),
         "proposals": result.get("proposals") or []},
        sort_keys=False, allow_unicode=True)
    path = edits_path(project_dir)
    text = header + body
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path, True


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

    paths, wf_changed = write_workflows(d, group, project, config)
    _, pl_changed = write_payload(d, group, project)
    payload = build_payload(d, group, project)

    detail = (f"{len(paths)} workflow(s), {len(payload['glossary_terms'])} term(s), "
              f"{len(payload['tags'])} tag(s)")
    if not (wf_changed or pl_changed):
        detail += ", unchanged"
    missing = [n for n in WORKFLOWS if not ingestion_path(d, n).exists()]
    if missing:
        # Named, not silent. A catalogue with no database workflow ingests a
        # vocabulary over zero tables, and that is indistinguishable from a
        # working setup until someone opens it.
        detail += f" · no {'/'.join(missing)} workflow (warehouse declares no OM connection)"
    probe = probe_engine()
    if not probe["ok"]:
        detail += f" · not ingested ({probe['detail'][:60]})"
    return StepResult("openmetadata", "ok", detail)


# ----------------------------------------------------------------- dagster --
def dagster_assets(ctx: ToolContext) -> ToolContribution:
    """The catalogue refresh, as an asset, a job and a schedule.

    **Asset**, downstream of this project's marts, so the catalogue describes
    the build that just happened. That is the whole point of hanging it off the
    models rather than off a timer: a catalogue refreshed independently of the
    warehouse drifts between runs and nobody can tell which state they are
    looking at.

    **Job**, so an operator can re-run just the catalogue without rebuilding the
    warehouse behind it — the common case when the OpenMetadata server was down
    or a token had expired.

    **Schedule**, off by default, for the case the asset dependency cannot
    cover: the ontology is edited without any model changing. Nothing upstream
    moves, so nothing triggers, and the glossary silently lags the YAML until
    someone next runs dbt.

    All three call `pf.scripts.catalog_sync`, which is also what `pf
    catalog sync` and a bare `python catalog_sync.py` call. One implementation
    on purpose: a scheduled job that has drifted from what a developer runs by
    hand is a job nobody trusts the morning it goes red.
    """
    from dagster import (
        AssetKey,
        DefaultScheduleStatus,
        MetadataValue,
        ScheduleDefinition,
        asset,
        define_asset_job,
    )

    project_dir = Path(ctx.project_dir)
    prefix = ctx.project.replace("-", "_")
    s = settings(ctx.config, ctx.group, ctx.project)
    asset_name = "catalog_sync"
    key = AssetKey([prefix, asset_name])

    @asset(
        name=asset_name,
        key_prefix=[prefix],
        group_name="catalog",
        # Marts, not the whole dbt graph: the catalogue is about what people
        # read, and hanging it off staging would refresh it on every raw-column
        # rename. Empty deps for a project with no manifest yet, which is a
        # scaffolded project — it still gets the asset, so the graph shows what
        # will happen rather than hiding it until the first build.
        deps=[AssetKey([prefix, m]) for m in _mart_models(project_dir)],
        description="Refresh graph, topology projections and OpenMetadata after a build.",
        compute_kind="openmetadata",
        metadata={"dagster/kind": "openmetadata", "tool": "openmetadata"},
    )
    def _catalog_sync(context) -> None:  # see dagster_runtime note on lazy imports
        from pf.scripts.catalog_sync import sync

        result = sync(Path(ctx.root), ctx.group, ctx.project)
        for stage in result.stages:
            log = context.log.info if stage.ok else context.log.error
            log("%s %s (%.2fs) %s", "ok" if stage.ok else "FAILED",
                stage.name, stage.seconds, stage.detail)

        context.add_output_metadata({
            "service": MetadataValue.text(s["service_name"]),
            "catalogue": MetadataValue.url(s["host_port"]),
            "stages_ok": MetadataValue.int(sum(1 for x in result.stages if x.ok)),
            "stages_failed": MetadataValue.int(sum(1 for x in result.stages if not x.ok)),
            "detail": MetadataValue.md(
                "\n".join(f"- `{x.name}` — {'ok' if x.ok else 'FAILED'} — {x.detail}"
                           for x in result.stages)),
        })
        if not result.ok:
            # Raised, not warned. A catalogue that silently half-published is
            # how a data owner ends up reading last week's glossary against this
            # week's tables.
            raise RuntimeError("catalog sync failed: "
                               + ", ".join(result.as_dict()["failed"]))

    job = define_asset_job(name=f"{prefix}_catalog_sync", selection=[key])
    schedule = ScheduleDefinition(
        name=f"{prefix}_catalog_sync_daily",
        job=job,
        cron_schedule="0 6 * * *",
        # Off until someone turns it on. A schedule that starts running the
        # moment a code location loads is a schedule that surprises whoever
        # deployed it, and this one talks to an external server.
        default_status=DefaultScheduleStatus.STOPPED,
        description="Catch ontology edits that changed no model, so triggered nothing.",
    )

    return ToolContribution(
        assets=[_catalog_sync],
        jobs=[job],
        schedules=[schedule],
        metadata={"openmetadata_url": s["host_port"]},
    )


def _mart_models(project_dir: Path) -> list[str]:
    """Mart model names from the dbt manifest, or none if it has not been built."""
    from pf.runtime.dbt_runtime import manifest as load_manifest

    man = load_manifest(project_dir)
    if not man:
        return []
    return sorted({
        str(n.get("name"))
        for n in (man.get("nodes") or {}).values()
        if n.get("resource_type") == "model"
        and "marts" in str(n.get("path") or "").replace("\\", "/").split("/")[:1]
    })


DOCS = """\
# OpenMetadata — the catalogue for {{group}}/{{project}}

The catalogue is where someone who does not read YAML finds out what a table
means. This project publishes into it automatically.

```bash
pf tool openmetadata payload {{group}} {{project}}   # what would be published
pf tool openmetadata sync {{group}} {{project}}      # regenerate the artefacts
pf tool openmetadata ingest {{group}} {{project}}    # database, then dbt
pf tool openmetadata pull {{group}} {{project}}      # owners' edits, as a proposal
pf tool doctor {{group}} {{project}}                 # can it actually reach the server
```

## What publishes what

| Source | Becomes |
|---|---|
| production warehouse | Schemas, tables, columns — `catalog/ingestion/database.yaml` |
| dbt `target/*.json` | Models, column-level lineage, tests, owners — `catalog/ingestion/dbt.yaml` |
| `platform/.../concepts.yaml` | Glossary terms, with identity and properties |
| ontology roles | `PlatformRole` tags; PII roles also get `PII.Sensitive` |
| topology relations | `relatedTerms` between glossary terms |
| policy layer | Glossary terms describing each constraint |
| knowledge graph metrics | OpenMetadata metrics, with their expressions |
| recce checks | Test cases carrying the review verdict |

**Order matters and is enforced.** The database pass catalogues tables; every
other row above describes tables. Run dbt ingestion alone against an empty
service and it has nothing to attach to — which is what this project did before
`catalog/ingestion/` existed, publishing a vocabulary over zero tables.

The catalogue points at **production**, never at your DuckDB file. The
connection comes from `pf.runtime.targets`, so the warehouse this project
deploys to and the one it catalogues cannot disagree.

## Owners can edit, in one direction with a return path

Nothing is read back automatically. Edit `concepts.yaml` and re-run — a change
made in the catalogue UI is overwritten on the next publish, on purpose. The
ontology is canonical and stays in git where `pf check` and the gate can judge
it.

That would make the catalogue read-only for the people who know the most, so
there is a proposal channel:

```bash
pf tool openmetadata pull {{group}} {{project}}
```

reads back descriptions, owners and column documentation, diffs them against
`contracts/annotations.yaml`, and writes the differences to
`catalog/owner-edits.yaml`. Nothing is applied. Move a line across by hand, in a
pull request, so a change to what a column means gets the review any other such
change gets.

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
        # All projections of things that live elsewhere. Editing any of them
        # forks the catalogue from the ontology it claims to publish — or, for
        # the ingestion workflows, from the warehouse the platform deploys to.
        "denylist": [f"**/{INGESTION_DIR}/**", f"**/{WORKFLOW_REL}",
                     f"**/{PAYLOAD_REL}"],
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
    # The projection and the REST publish need no client; only `ingest` does,
    # and it reports the CLI's absence itself. See spec.Tool.offline.
    offline=True,
    # The catalogue is downstream of everything it publishes, so it is
    # bootstrapped last. `recce` writes the recorded checks this turns into
    # OpenMetadata test cases, and `wren` writes the MDL manifest that names
    # which published entity a model backs. Run alphabetically — which is what
    # bootstrap did before `Tool.after` existed — this ran *first* and
    # catalogued a project whose review and semantic layer had not been
    # generated yet, producing a catalogue that looked complete and carried
    # neither.
    after=("recce", "wren"),
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
    dbt=DbtBinding(needs_manifest=True,
                   artefacts=(INGESTION_DIR, PAYLOAD_REL)),
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
        paths, changed = write_workflows(d, group, project, None)
        for path in paths:
            mark = "[green]wrote[/]" if path.stem in changed else "[dim]unchanged[/]"
            console.print(f"  {mark} {path}")
        if "-ingestion.yaml" in changed:
            console.print("  [yellow]removed[/] catalog/ingestion.yaml "
                          "[dim](superseded by catalog/ingestion/)[/]")
        missing = [n for n in WORKFLOWS if not ingestion_path(d, n).exists()]
        if missing:
            console.print(f"  [yellow]![/] no {', '.join(missing)} workflow — the "
                          "production warehouse declares no OpenMetadata connection")
        pl, pl_changed = write_payload(d, group, project)
        console.print(f"  {'[green]wrote[/]' if pl_changed else '[dim]unchanged[/]'} {pl}")

    @om.command("ingest")
    def cmd_ingest(group: str, project: str,
                   only: str = typer.Option("", "--only",
                                            help=f"one of: {', '.join(WORKFLOWS)}")) -> None:
        """Run the ingestion workflows against the configured server.

        Database first, then dbt. The order is a dependency: dbt ingestion
        enriches tables the database pass catalogued, so it has nothing to
        attach to on its own.
        """
        results = ingest(_pdir(group, project), only=only)
        for r in results:
            console.print(
                f"[green]✓[/] {r['workflow']}" if r["ok"]
                else f"[red]✗[/] {r['workflow']} — {r.get('reason')}: "
                     f"{str(r.get('message', ''))[:400]}")
        if not all(r["ok"] for r in results):
            raise typer.Exit(1)

    @om.command("publish")
    def cmd_publish(group: str, project: str) -> None:
        """Send the glossary, role tags and metrics to OpenMetadata.

        Needs no database service and no warehouse credentials — this is
        vocabulary, not tables — so it works against a local server and while
        the production warehouse is unreachable.
        """
        d = _pdir(group, project)
        result = publish_payload(d, group, project, None)
        for key, n in result["sent"].items():
            console.print(f"  [green]↑[/] {key}: {n}")
        for f in result["failed"][:10]:
            console.print(f"  [red]✗[/] {f}")
        if result["failed"]:
            console.print(f"[red]{len(result['failed'])} failed[/] → {result['host']}")
            raise typer.Exit(1)
        console.print(f"[green]✓[/] published to {result['host']}")

    @om.command("pull")
    def cmd_pull(group: str, project: str) -> None:
        """Read data owners' edits out of the catalogue, as a reviewable proposal.

        Writes `catalog/owner-edits.yaml` and nothing else. `contracts/` is
        canonical and is never touched here — moving a line across is a pull
        request, so a change to what a column means gets reviewed like one.
        """
        d = _pdir(group, project)
        result = pull_edits(d, group, project, None)
        if not result["ok"]:
            console.print(f"[red]✗[/] {result['reason']}: {result['message'][:400]}")
            raise typer.Exit(1)
        path, changed = write_edits(d, result)
        n = len(result["proposals"])
        console.print(f"[green]✓[/] {result['tables']} table(s) in "
                      f"{result['service']} · {n} proposal(s)")
        console.print(f"  {'[green]wrote[/]' if changed else '[dim]unchanged[/]'} {path}")
        if n:
            console.print("  [dim]review and move to contracts/annotations.yaml "
                          "in a pull request[/]")

    app.add_typer(om, name="openmetadata")
