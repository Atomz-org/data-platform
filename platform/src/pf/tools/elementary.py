"""Elementary — data observability recorded inside the warehouse itself.

The platform already answers "what could break" (`pf impact`) and "what did a
change do" (recce). Elementary answers the question between runs: *is the data
healthy right now, and what has every test said about it over time?* Its dbt
package hooks `on-run-start`/`on-run-end` in every `dbt build` and writes run
results, test results, model timings and schema snapshots into an
`elementary` schema beside the marts — so observability is a set of queryable
tables with history, not a log file that scrolled away. The `edr` CLI then
renders those tables into a self-contained HTML report.

## Why this is a dbt package first and a tool second

Everything Elementary records comes from hooks *inside* the dbt run, so
"enabled" means "declared in this project's `packages.yml`". That is the whole
integration: once the package is declared, every `dbt build` — from `pf seed`,
from Dagster, from a laptop — feeds the observability tables with no further
wiring, and the results of every other tool's dbt tests (dbt-expectations
included) are collected too. The bootstrap hook below makes exactly two
declarations and owns nothing else:

    packages.yml       elementary-data/elementary   (untouched if already pinned)
    dbt_project.yml    models: elementary: +schema: elementary

The version range pins the minor: Elementary's own models migrate between
minors, and a silent jump would change the schema under the `edr` CLI, which
is version-locked to the package.

## The CLI is optional, the recording is not

The package needs nothing installed beyond dbt. `edr` (the pypi package
`elementary-data`) is only needed to render the report and connects through
the `elementary` profile this tool appends to profiles.yml — pointed at the
same DuckDB file as the project, schema `main_elementary`, which is where
dbt's default schema naming (`<target schema>_<custom schema>`) puts the
package's models on the dev target. A machine without `edr` still records
everything; the report is the part that degrades.

The CLI installs *isolated* (`uv tool install elementary-data==0.25.* --with dbt-duckdb`),
never as a workspace extra: elementary-data pins posthog<3 and recce needs
posthog>=3, so one lockfile cannot hold both — the openmetadata-ingestion
situation exactly, resolved the same way. `pf` shells out and imports nothing.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from pf.capabilities import Capability
from pf.tools import dbtproject
from pf.tools.spec import (
    DbtBinding,
    Requirement,
    Surface,
    Tool,
    ToolContext,
    ToolContribution,
)

#: The dbt package, as the hub names it. The GitHub repo is
#: `elementary-data/dbt-data-reliability`; the pypi CLI is `elementary-data`.
PACKAGE = "elementary-data/elementary"
#: Minor-pinned on purpose — see the module docstring.
PACKAGE_VERSION = [">=0.25.0", "<0.26.0"]
#: Custom schema for the package's models. With dbt's default schema naming
#: and the DuckDB dev target this lands in `main_elementary`.
SCHEMA = "elementary"
#: Where `edr report` writes, relative to the dbt project directory.
EDR_TARGET = "edr_target"
REPORT_FILE = "elementary_report.html"
DEFAULT_PORT = 8020


# ------------------------------------------------------------------ paths --
def dbt_dir(project_dir: Path) -> Path:
    return Path(project_dir) / "transform"


def report_dir(project_dir: Path) -> Path:
    return dbt_dir(project_dir) / EDR_TARGET


def report_file(project_dir: Path) -> Path:
    return report_dir(project_dir) / REPORT_FILE


def has_manifest(project_dir: Path) -> bool:
    return (dbt_dir(project_dir) / "target" / "manifest.json").exists()


# ------------------------------------------------------------------ setup --
def models_block(schema: str = SCHEMA) -> str:
    """The `models:` child declaring where the package's models land.

    Two-space indented for insertion as the first child of `models:`; comments
    travel with it so the file explains itself to the next reader.
    """
    return (
        "  # Elementary's observability models (run results, test history, schema\n"
        "  # snapshots), written by the package's on-run-end hooks on every dbt build.\n"
        "  # The schema keeps them out of the marts. Managed by `pf tool elementary`.\n"
        "  elementary:\n"
        f"    +schema: {schema}\n"
    )


def derive_profile(project_profiles: dict[str, Any],
                   schema: str = SCHEMA) -> dict[str, Any]:
    """The `elementary` profile as a mapping, mirroring every project target.

    `edr` connects with a profile named `elementary` that must resolve to
    wherever the package's tables actually are — and that is a *per-target*
    fact: `main_<schema>` in the dev DuckDB file, `ANALYTICS_<schema>` on the
    Snowflake prod, `analytics_<schema>` inside a DuckLake catalog. A profile
    hardcoded to one engine makes observability a dev-only feature, which is
    backwards — production is where the history matters most.

    So the profile is derived, not written: one elementary output per project
    target, identical connection, schema suffixed the way dbt's default
    `generate_schema_name` composes it (`<target schema>_<custom schema>`).
    The `target:` selector is copied verbatim, so the same `DBT_TARGET` that
    picks where dbt builds picks which side `edr` reads.
    """
    import copy

    for prof in project_profiles.values():
        if isinstance(prof, dict) and isinstance(prof.get("outputs"), dict):
            outputs, target = prof["outputs"], prof.get("target", "dev")
            break
    else:
        return {}

    derived: dict[str, Any] = {}
    for tname, out in outputs.items():
        if not isinstance(out, dict):
            continue
        o = copy.deepcopy(out)
        if "schema" in o:
            o["schema"] = f"{o['schema']}_{schema}"
        elif "dataset" in o:  # BigQuery's name for the same idea
            o["dataset"] = f"{o['dataset']}_{schema}"
        else:  # DuckDB targets rarely name one; the engine default is `main`
            o["schema"] = f"main_{schema}"
        derived[tname] = o
    if not derived:
        return {}
    return {"elementary": {"target": target, "outputs": derived}}


def profile_block(project_dir: Path, schema: str = SCHEMA) -> str:
    """The derived `elementary` profile, rendered for profiles.yml."""
    import yaml

    doc = derive_profile(
        dbtproject.load_yaml(dbt_dir(project_dir) / "profiles.yml"), schema)
    if not doc:
        return ""
    return (
        "# How the Elementary CLI (`edr`) reads the tables the dbt package writes.\n"
        "# DERIVED from the project profile above by `pf tool elementary`: one\n"
        "# elementary output per project target, schema suffixed the way dbt\n"
        "# composes custom schemas, so `DBT_TARGET=prod edr report` reads the\n"
        "# production warehouse and the default reads dev. Regenerated by\n"
        "# `pf bootstrap` — retarget the project, not this block.\n"
        + yaml.safe_dump(doc, sort_keys=False)
    )


def ensure_package(project_dir: Path, version: list[str] | None = None) -> bool:
    return dbtproject.ensure_package(dbt_dir(project_dir), PACKAGE,
                                     version or PACKAGE_VERSION)


def ensure_models_config(project_dir: Path, schema: str = SCHEMA) -> bool:
    """Declare the package's schema in dbt_project.yml. True if added."""
    d = dbt_dir(project_dir)
    if dbtproject.has_project_key(d, "models", "elementary"):
        return False
    return dbtproject.insert_under_key(d / "dbt_project.yml", "models",
                                       models_block(schema))


def ensure_profile(project_dir: Path, schema: str = SCHEMA) -> bool:
    """Emit the derived profile, replacing a stale one. True if it changed.

    A replace, not an append: the block is a function of the project's own
    targets, and those move — `pf capability-add ducklake` swaps `prod`, and
    an elementary profile still pointing at Snowflake would send `edr` to a
    warehouse the project no longer builds in.
    """
    block = profile_block(project_dir, schema)
    if not block:
        return False
    return dbtproject.replace_profile(dbt_dir(project_dir), "elementary", block)


# -------------------------------------------------------------------- run --
def dbt_env(project_dir: Path) -> dict[str, str]:
    """Environment for edr, whose embedded dbt resolves our profiles.yml.

    The same two variables `pf.runtime.dbt_runtime.dbt()` sets, for the same
    reason recce's copy exists: profiles.yml reads the warehouse path from
    `PF_DUCKDB_PATH`, and without it every invocation dies in dbt's Jinja
    renderer with an error that reads like a tool bug and is not one.
    """
    import os

    from pf.runtime.warehouse import Warehouse

    d = Path(project_dir)
    group = d.parents[1].name if len(d.parents) >= 2 else ""
    wh = Warehouse.for_project(d, group, d.name)
    env = dict(os.environ)
    env.setdefault("DBT_TARGET", "dev")
    env["PF_DUCKDB_PATH"] = str(wh.path)
    wh.ensure_dir()
    return env


def build_models(project_dir: Path) -> dict[str, Any]:
    """Materialise the package's own models (`dbt run --select elementary`).

    Needed once after enabling — the on-run-end hooks *append to* these tables
    but only the models create them — and harmless afterwards. Ordinary
    project builds keep them fresh without this, since the package's models
    are part of the project graph.
    """
    from pf.runtime.dbt_runtime import dbt

    env = dbt_env(project_dir)
    proc = dbt(project_dir, "run", "--select", "elementary",
               duckdb_path=env["PF_DUCKDB_PATH"])
    return {"ok": proc.returncode == 0,
            "message": (proc.stdout or proc.stderr or "")[-2000:]}


def run_report(project_dir: Path, timeout: int = 900) -> dict[str, Any]:
    """Render the observability report with `edr`. Never raises on failure.

    A report that could not be produced is a *finding* for the caller to
    surface — a Dagster asset and a CLI command want to phrase it differently,
    and neither wants "edr is not installed" dressed up as a stack trace.
    """
    d = dbt_dir(project_dir)
    args = [
        "edr", "report",
        "--project-dir", str(d),
        "--profiles-dir", str(d),
        # Self-contained output beside the other dbt artefacts; edr resolves
        # this relative to its cwd, which is why cwd is the dbt project.
        "--target-path", EDR_TARGET,
    ]
    try:
        proc = subprocess.run(args, cwd=str(d), env=dbt_env(project_dir),
                              capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return {"ok": False, "reason": "not_installed",
                "message": "edr is not on PATH — "
                           "`uv tool install elementary-data==0.25.* --with dbt-duckdb`"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "timeout", "message": "edr report timed out"}

    produced = report_file(project_dir).exists()
    return {
        "ok": proc.returncode == 0 and produced,
        "reason": "" if proc.returncode == 0 and produced else "report_failed",
        "returncode": proc.returncode,
        "message": (proc.stderr or proc.stdout or "")[-2000:],
        "report": str(report_file(project_dir)) if produced else "",
    }


# --------------------------------------------------------------- bootstrap --
def bootstrap_project(root: Path, group: str, project: str,
                      project_dir: Path, config: dict[str, Any]) -> Any:
    """Idempotent per-project setup. Called by `pf bootstrap`.

    Declarations only — nothing here runs dbt. The package installs on the
    next `dbt deps` (every `pf seed` runs one) and its tables appear on the
    first build after that, which keeps bootstrap fast and working on a
    machine with no warehouse.
    """
    from pf.scaffold.bootstrap import StepResult

    if not (dbt_dir(project_dir) / "dbt_project.yml").exists():
        return StepResult("elementary", "skipped", "no dbt project")

    # `tools.yaml` config is the per-family/per-entity dial: a group that wants
    # a different schema or has qualified a newer package minor states it once
    # and every sister inherits — no code edit, which is the whole point of a
    # tool being declarative.
    #
    #   tools:
    #     elementary:
    #       enabled: true
    #       config:
    #         schema: elementary          # dbt_project.yml +schema; the edr
    #                                     # profile derives from it per target
    #         version: [">=0.25.0", "<0.26.0"]
    schema = str(config.get("schema") or SCHEMA)
    version = list(config.get("version") or PACKAGE_VERSION)

    added_pkg = ensure_package(project_dir, version)
    added_cfg = ensure_models_config(project_dir, schema)
    added_profile = ensure_profile(project_dir, schema)

    changed = [what for what, did in (
        ("packages.yml", added_pkg), ("dbt_project.yml", added_cfg),
        ("profiles.yml", added_profile)) if did]
    detail = ("declared in " + ", ".join(changed)) if changed else "declared, unchanged"
    if added_pkg:
        detail += " · tables appear on the next `pf seed`"
    return StepResult("elementary", "ok", detail)


# ----------------------------------------------------------------- dagster --
def dagster_assets(ctx: ToolContext) -> ToolContribution:
    """One `elementary_report` asset, downstream of the marts it observes.

    The *recording* needs no asset — the package's hooks ride along inside
    every dbt build. This asset is the rendering half: refresh the report from
    the tables those hooks wrote. It degrades to metadata rather than failing
    when `edr` is absent, per the tool's `offline` contract.
    """
    import json

    from dagster import AssetKey, MetadataValue, asset

    project_dir = Path(ctx.project_dir)
    if not has_manifest(project_dir):
        return ToolContribution()

    prefix = ctx.project.replace("-", "_")
    port = int(ctx.config.get("port", DEFAULT_PORT))

    def _marts() -> list[str]:
        p = dbt_dir(project_dir) / "target" / "manifest.json"
        try:
            manifest = json.loads(p.read_text())
        except Exception:  # noqa: BLE001 — no manifest, no deps
            return []
        return sorted(
            n["name"] for n in (manifest.get("nodes") or {}).values()
            if n.get("resource_type") == "model"
            and (n.get("path") or "").split("/")[0] == "marts")

    deps = [AssetKey([prefix, name]) for name in _marts()]

    @asset(
        name="elementary_report",
        key_prefix=[prefix],
        group_name="observability",
        deps=deps,
        description="Elementary observability report — run history, test "
                    "results and schema changes, rendered from the tables the "
                    "dbt package records on every build.",
        compute_kind="elementary",
        metadata={"dagster/kind": "elementary", "tool": "elementary"},
    )
    def _elementary_report(context) -> None:  # noqa: ANN001 — see dagster_runtime note
        result = run_report(project_dir)
        meta: dict[str, Any] = {
            "status": "ok" if result.get("ok") else result.get("reason", "failed"),
            "report_ui": MetadataValue.url(f"http://127.0.0.1:{port}/{REPORT_FILE}"),
        }
        if result.get("report"):
            meta["report_file"] = result["report"]
        if not result.get("ok"):
            # A report that could not render is a warning, not a failed asset:
            # the recording — the part that matters for history — happened in
            # the dbt build upstream of this node regardless.
            context.log.warning(result.get("message", ""))
        context.add_output_metadata(meta)

    return ToolContribution(
        assets=[_elementary_report],
        metadata={"elementary_url": f"http://127.0.0.1:{port}/{REPORT_FILE}"},
    )


# ------------------------------------------------------------- capability --
ELEMENTARY_DOCS = """\
# Elementary — data observability for {{group}}/{{project}}

Every `dbt build` here records itself: the `elementary-data/elementary`
package hooks on-run-start/on-run-end and writes run results, test results
(dbt's own, dbt-expectations', everyone's), model timings and schema snapshots
into the `main_elementary` schema beside the marts. Observability is queryable
tables with history, not a log that scrolled away.

## The loop

```bash
pf seed {{group}} {{project}}                     # every build records itself
pf tool elementary run {{group}} {{project}}      # first time: create the tables
pf tool elementary report {{group}} {{project}}   # render the HTML report
pf tool elementary serve {{group}} {{project}}    # read it in a browser
```

`report` and `serve` need the CLI, installed isolated (it cannot share a
lockfile with recce): `uv tool install elementary-data==0.25.* --with dbt-duckdb`.
Recording needs nothing — the package rides inside dbt.

## What is declared where

| file | declaration | owner |
|---|---|---|
| `transform/packages.yml` | the package, minor-pinned | `pf bootstrap` adds, your pin wins |
| `transform/dbt_project.yml` | `models: elementary: +schema` | inserted once, then yours |
| `transform/profiles.yml` | the `elementary` profile `edr` connects with | regenerated by bootstrap |

The `elementary` profile is derived per target, so `DBT_TARGET=prod edr report`
reads production — retarget the project, not that block.

`transform/edr_target/` is a build artefact (the rendered report) and is
gate-denied like `target/` — regenerate it, never edit it.

## Anomaly detection

The package also ships anomaly tests (`elementary.volume_anomalies`,
`elementary.freshness_anomalies`, ...). They are deliberately not generated:
an anomaly threshold is a judgement about one table's behaviour, so declare
them in the model's own yml where that judgement lives. The
`elementary-observe` skills are the how — `add-anomaly-tests` to declare a
monitor (with `jaffle/jaffle-shop`'s marts as the worked example, after
Elementary's own jaffle-shop-goes-online demo), `triage-observability` to
read what fired. Results land in the same tables and the same report.

## In Dagster

The `elementary_report` asset runs downstream of this project's marts and
attaches the report link. The recording itself has no asset — it happens
inside every dbt build already.
"""

CAPABILITY = Capability(
    name="elementary",
    description="Data observability recorded in-warehouse on every dbt build.",
    files={"docs/elementary.md": ELEMENTARY_DOCS},
    settings={
        "permissions": {"allow": [
            "Bash(pf tool elementary:*)",
            "Bash(edr report:*)", "Bash(edr monitor:*)",
        ]},
        # The skills half: declaring anomaly monitors and triaging what the
        # recording says. Enabling the tool without them leaves an agent that
        # collects observability it was never taught to read.
        "enabledPlugins": {"elementary-observe@platform": True},
    },
    gate={
        # The rendered report is a build artefact of the tables it was rendered
        # from; editing it makes the record disagree with the warehouse.
        "denylist": ["**/transform/edr_target/**"],
    },
)


# ------------------------------------------------------------------- tool --
TOOL = Tool(
    name="elementary",
    title="Elementary",
    summary="Data observability — every dbt build records run and test "
            "history into the warehouse; `edr` renders the report.",
    url="https://github.com/elementary-data/elementary",
    # A family decides once that its builds are observed; sisters differ in
    # business logic, not in whether their runs are recorded.
    scope=frozenset({"project", "group"}),
    capability=CAPABILITY,
    default_enabled=True,
    # Bootstrap is pure declaration — three file edits that need nothing
    # installed. Skipping it on a machine without `edr` would make the
    # *recording* depend on who ran the scaffolder, which is the exact failure
    # `offline` exists for. The hooks that do drive the binary degrade inline.
    offline=True,
    # The CLI as a binary only — never a python module requirement, because it
    # installs isolated (`uv tool install`) where our interpreter cannot import
    # it, and a requirement that can never be satisfied reads as permanently
    # broken in `pf tool doctor`. The module docstring has the lockfile story.
    requires=(
        Requirement("binary", "edr",
                    "uv tool install elementary-data==0.25.* --with dbt-duckdb"),
    ),
    # Recce's bootstrap regenerates profiles.yml wholesale when the `base`
    # target is missing; running after it means the `elementary` profile this
    # tool appends survives that rewrite instead of vanishing until the next
    # bootstrap. An absent recce satisfies the ordering by contract.
    after=("recce",),
    dbt=DbtBinding(
        needs_manifest=True,
        artefacts=(f"transform/{EDR_TARGET}",),
    ),
    surface=Surface(
        port=DEFAULT_PORT,
        path=f"/{REPORT_FILE}",
        embeddable=True,
        start=("python", "-m", "http.server", "{port}",
               "--directory", "{dbt_dir}/" + EDR_TARGET),
    ),
    bootstrap="pf.tools.elementary:bootstrap_project",
    dagster="pf.tools.elementary:dagster_assets",
    commands="pf.tools.elementary:register_commands",
    stack_layer={
        "layer": "observability", "title": "Observability (Elementary)",
        "upstream": "elementary", "toolkits": ["elementary-observe"],
        "artefacts": f"transform/{EDR_TARGET}/{REPORT_FILE}", "node_kinds": [],
    },
)


# -------------------------------------------------------------------- cli --
def register_commands(app: Any) -> None:
    """Attach `pf tool elementary ...`. Imported lazily by the CLI."""
    import typer
    from rich.console import Console

    console = Console()
    el_app = typer.Typer(help="Elementary: in-warehouse observability of every dbt build.")

    def _pdir(group: str, project: str) -> Path:
        from pf.cli import pdir
        return pdir(group, project)

    @el_app.command("run")
    def cmd_run(group: str, project: str) -> None:
        """Create/refresh the package's own tables (`dbt run --select elementary`)."""
        d = _pdir(group, project)
        result = build_models(d)
        mark = "[green]✓[/]" if result["ok"] else "[red]✗[/]"
        console.print(f"{mark} elementary models "
                      f"{'built' if result['ok'] else 'failed'}")
        if not result["ok"]:
            console.print(result["message"])
            raise typer.Exit(1)

    @el_app.command("report")
    def cmd_report(group: str, project: str) -> None:
        """Render the observability report with `edr`."""
        d = _pdir(group, project)
        result = run_report(d)
        if result.get("reason") == "not_installed":
            console.print(f"[yellow]{result['message']}[/]")
            raise typer.Exit(1)
        if not result.get("ok"):
            console.print(f"[red]report failed[/]\n{result.get('message', '')}")
            raise typer.Exit(1)
        console.print(f"[green]✓[/] {result['report']}")

    @el_app.command("serve")
    def cmd_serve(group: str, project: str,
                  port: int = typer.Option(DEFAULT_PORT),
                  host: str = typer.Option("127.0.0.1")) -> None:
        """Serve the rendered report over HTTP."""
        import os
        import sys

        d = _pdir(group, project)
        if not report_file(d).exists():
            console.print("[yellow]![/] no report yet — "
                          f"`pf tool elementary report {group} {project}` first")
            raise typer.Exit(1)
        console.print(f"[green]→[/] http://{host}:{port}/{REPORT_FILE}")
        os.execv(sys.executable, [sys.executable, "-m", "http.server", str(port),
                                  "--bind", host, "--directory", str(report_dir(d))])

    app.add_typer(el_app, name="elementary")
