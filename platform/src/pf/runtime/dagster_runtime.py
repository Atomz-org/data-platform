"""The Dagster factory.

Note on imports: dagster is imported lazily inside functions so the rest of the
platform works without the orchestration extra installed. Combined with
`from __future__ import annotations`, that means **no dagster type may appear in
a function signature** — Dagster resolves annotations at module scope and would
fail with NameError. Asset context params are therefore unannotated.

A project's definitions.py is ~10 lines because this module owns everything that
must be identical across every project: the DuckDB writer pool, dlt and dbt asset
wiring, and the lineage that joins them.

Lineage is the reason dbt models are emitted through `@dbt_assets` rather than a
single shelled-out `dbt build`: one opaque asset draws no edges. The translator
below maps each dbt *source* onto the dlt asset that lands it, which is what
stitches ingestion and transformation into one graph.

The `dagster-orchestrate` toolkit is explicitly constrained to never scaffold a
raw `Definitions` object — assets go in `src/<project>/defs/`, assembly happens here.
"""

from __future__ import annotations

import importlib
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pf.runtime.warehouse import Warehouse


def build_definitions(
    *,
    group: str,
    project: str,
    project_dir: str | Path | None = None,
    source_modules: Sequence[str] = (),
    dbt_project_dir: str = "transform",
    sisters: dict[str, str] | None = None,
) -> Any:
    """Assemble a Dagster `Definitions` for one project.

    Args:
        group: Group slug, e.g. "acme".
        project: Project slug, e.g. "acme-us".
        project_dir: Project root. Pass it explicitly; cwd is not reliable
            inside a Dagster code-location subprocess.
        source_modules: Dotted module paths holding annotated dlt sources.
            Leave empty (the default) to auto-discover every module under
            `src/<module>/sources/`.
        dbt_project_dir: Relative path to the dbt project.
        sisters: alias -> duckdb path, for a roll-up project only. Relative
            paths are resolved against `project_dir`, never against cwd —
            Dagster runs a code location with cwd set to its
            `working_directory` (`<project>/src`), so "../acme-us/..." in a
            project's definitions.py would otherwise resolve one level too deep.
    """
    from dagster import Definitions, define_asset_job, multiprocess_executor

    root = Path(project_dir) if project_dir else Path.cwd()
    wh = Warehouse.for_project(root, group, project)

    # dbt's profiles.yml reads this; set it before any manifest is loaded.
    os.environ.setdefault("PF_DUCKDB_PATH", str(wh.path))
    os.environ["PF_DUCKDB_PATH"] = str(wh.path)

    assets: list[Any] = []
    resources: dict[str, Any] = {}

    for mod_path in source_modules or _discover_source_modules(root, project):
        module = importlib.import_module(mod_path)
        for res_name, resource in _annotated(module).items():
            assets.append(_make_ingest_asset(res_name, resource, wh, mod_path))

    dbt_dir = root / dbt_project_dir
    if (dbt_dir / "dbt_project.yml").exists():
        dbt_asset, dbt_resource = _make_dbt_assets(dbt_dir, wh)
        if dbt_asset is not None:
            assets.append(dbt_asset)
            resources["dbt"] = dbt_resource

    if sisters:
        assets.append(_make_rollup_asset(wh, _resolve_sisters(root, sisters)))

    # Tools contribute last, so a tool asset can depend on the dbt models above.
    # Nothing here names a tool: which ones run comes from the project's
    # tools.yaml, and a tool installed from outside this repo lands the same way.
    asset_checks: list[Any] = []
    tool_metadata: dict[str, Any] = {}
    for contrib in _tool_contributions(root, group, project, wh):
        assets.extend(contrib.assets)
        asset_checks.extend(contrib.asset_checks)
        resources.update(contrib.resources)
        tool_metadata.update(contrib.metadata)

    job = define_asset_job(name=f"{project.replace('-', '_')}_all", selection="*")

    return Definitions(
        assets=assets,
        asset_checks=asset_checks,
        jobs=[job],
        resources=resources,
        executor=multiprocess_executor.configured({"max_concurrent": 4}),
        # Tool metadata (a UI URL, say) rides on the Definitions so an operator
        # can find a tool's own surface from Dagster. Dagster OSS has no
        # custom-tab extension point — see pf.tools.__init__ for what that means
        # and where the combined view actually lives.
        metadata={"group": group, "project": project, "warehouse": str(wh.path),
                  **tool_metadata},
    )


def _tool_contributions(root: Path, group: str, project: str, wh: Any) -> list[Any]:
    """Enabled tools' Dagster contributions, or nothing if the layer is absent.

    Wrapped because a code location that raises on import disappears from
    Dagster entirely. An optional tool must never be able to do that to a
    project's real assets.
    """
    try:
        from pf.tools import dagster_contributions
    except Exception:  # noqa: BLE001 — platform without the tools layer
        return []
    # Repo root from the project path, not from cwd: a Dagster code location runs
    # with cwd set to `<project>/src`, so anything cwd-derived resolves wrong.
    # `groups/<group>/projects/<project>` puts the root four levels up.
    repo_root = root.parents[3] if len(root.parents) >= 4 else root
    try:
        return dagster_contributions(
            root=repo_root, group=group, project=project, project_dir=root,
            dbt_dir=root / "transform", warehouse=wh)
    except Exception as exc:  # noqa: BLE001
        import warnings
        warnings.warn(f"tool contributions skipped: {type(exc).__name__}: {exc}",
                      stacklevel=2)
        return []


def _discover_source_modules(root: Path, project: str) -> list[str]:
    """Every module under `src/<module>/sources/`.

    Dropping a new annotated source file into that directory is enough — no
    edit to definitions.py. `source_modules` stays as an explicit override for
    the rare case where a project needs to exclude one.
    """
    module = _prefix(project)
    sources = root / "src" / module / "sources"
    if not sources.is_dir():
        return []
    return [
        f"{module}.sources.{f.stem}"
        for f in sorted(sources.glob("*.py"))
        if not f.stem.startswith("_")
    ]


def _annotated(module: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name in dir(module):
        obj = getattr(module, name)
        if getattr(obj, "__pf_annotation__", None) is not None:
            out[getattr(obj, "name", name)] = obj
    return out


def _prefix(project: str) -> str:
    """Asset-key namespace. Sisters have identically-named models, so every key
    is prefixed with the project or they collide across code locations."""
    return project.replace("-", "_")


# ------------------------------------------------------------------ ingest --
def _make_ingest_asset(name: str, resource: Any, wh: Warehouse, mod_path: str):
    from dagster import MetadataValue, asset

    ann = resource.__pf_annotation__
    source = ann.source or "raw"

    @asset(
        name=name,
        key_prefix=[_prefix(wh.project)],
        group_name="ingest",
        pool=wh.writer_pool,          # per-project: sisters never queue behind each other
        description=ann.description or f"dlt resource {name}",
        metadata={"concept": ann.concept, "grain": ann.grain, "module": mod_path,
                  "source": source, "dagster/kind": "dlt"},
        compute_kind="dlt",
    )
    def _ingest(context) -> None:  # noqa: ANN001 — see module note on lazy imports
        from pf.runtime.dlt_runtime import run_source

        # The dataset is the dlt *source* ("stripe"), never the resource name.
        # Keying it by resource landed `charges.charges` while dbt read
        # `stripe.charges`, so ingestion and transformation silently ran against
        # different tables: dbt kept building green on whatever a previous
        # `pf seed` had left behind. The graph agrees with dbt here —
        # `table:stripe.charges` is the node id — so the source wins.
        info = run_source(wh, resource, source_name=source, dataset=source)
        context.add_output_metadata({
            "concept": ann.concept,
            "load_ids": MetadataValue.json(info["load_ids"]),
            "dataset": info["dataset"],
        })

    return _ingest


# --------------------------------------------------------------------- dbt --
def _translator(project: str):
    """Map dbt nodes onto platform asset keys.

    A dbt *source* resolves to the dlt asset that lands it — that single mapping
    is what connects ingestion to transformation in the asset graph. Everything
    else is namespaced under the project.
    """
    from dagster import AssetKey
    from dagster_dbt import DagsterDbtTranslator

    prefix = _prefix(project)

    class PlatformTranslator(DagsterDbtTranslator):
        def get_asset_key(self, dbt_resource_props: dict[str, Any]) -> AssetKey:
            if dbt_resource_props.get("resource_type") == "source":
                # dlt lands `stripe.charges` as the asset <project>/charges
                return AssetKey([prefix, dbt_resource_props["name"]])
            return AssetKey([prefix, dbt_resource_props["name"]])

        def get_group_name(self, dbt_resource_props: dict[str, Any]) -> str | None:
            path = (dbt_resource_props.get("path") or "").split("/")
            return path[0] if path and path[0] else "transform"

        def get_description(self, dbt_resource_props: dict[str, Any]) -> str:
            return dbt_resource_props.get("description") or ""

    return PlatformTranslator()


def _make_dbt_assets(dbt_dir: Path, wh: Warehouse):
    """One asset per dbt model, so lineage is real rather than a single black box."""
    from dagster_dbt import DbtCliResource, dbt_assets

    manifest = dbt_dir / "target" / "manifest.json"
    if not manifest.exists():
        # No manifest yet (a freshly scaffolded project). Emitting nothing is
        # correct — a stub asset would draw a node with no lineage, which is the
        # exact problem this function exists to avoid.
        return None, None

    resource = DbtCliResource(project_dir=str(dbt_dir), profiles_dir=str(dbt_dir))

    @dbt_assets(
        manifest=manifest,
        dagster_dbt_translator=_translator(wh.project),
        pool=wh.writer_pool,
        required_resource_keys={"dbt"},
    )
    def _dbt(context):  # noqa: ANN001
        # The resource is pulled off the context rather than taken as a
        # parameter: an unannotated `dbt` param is read as an asset input, and
        # an annotated one hits the lazy-import problem noted at module level.
        yield from context.resources.dbt.cli(["build"], context=context).stream()

    return _dbt, resource


# ------------------------------------------------------------------ rollup --
def _resolve_sisters(root: Path, sisters: dict[str, str]) -> dict[str, Path]:
    """Anchor sister database paths to the project root rather than to cwd."""
    return {
        alias: Path(p) if Path(p).is_absolute() else (root / p).resolve()
        for alias, p in sisters.items()
    }


def _make_rollup_asset(wh: Warehouse, sisters: dict[str, Path]):
    """Cross-entity roll-up.

    `deps` are plain AssetKeys pointing into the sisters' code locations —
    Dagster resolves cross-location dependencies by key, so the roll-up shows
    upstream lineage without importing a sister's code.
    """
    from dagster import AssetKey, MetadataValue, asset

    # The sister's project slug is <group>-<alias>. This was hardcoded to
    # "acme-", so any other group's roll-up drew dependencies on asset keys that
    # do not exist — silently, since cross-location deps resolve by key.
    upstream = [AssetKey([_prefix(f"{wh.group}-{alias}"), "fct_revenue"]) for alias in sisters]

    @asset(
        name="group_rollup",
        key_prefix=[_prefix(wh.project)],
        group_name="rollup",
        pool=wh.writer_pool,
        deps=upstream,
        description="Cross-entity roll-up. Attaches sister databases READ_ONLY.",
        compute_kind="duckdb",
    )
    def _rollup(context) -> None:  # noqa: ANN001
        paths = {alias: Path(p) for alias, p in sisters.items()}
        with wh.attach_sisters(paths) as con:
            unions = " UNION ALL ".join(
                f"SELECT '{alias.upper()}' AS entity, * FROM {alias}.main_marts.fct_revenue"
                for alias in paths
            )
            con.execute(f"CREATE OR REPLACE TABLE group_revenue AS {unions}")
            rows = con.execute("SELECT count(*) FROM group_revenue").fetchone()[0]
        context.add_output_metadata({"entities": MetadataValue.json(list(paths)), "rows": rows})

    return _rollup
