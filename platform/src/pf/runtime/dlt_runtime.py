"""dlt pipeline factory. Projects declare annotated sources; the platform owns
destination wiring, naming, schema contracts and annotation export.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pf.ontology.annotate import export_annotations
from pf.runtime.warehouse import Warehouse

# Contract applied to every pipeline unless a source overrides it. `evolve` on
# columns keeps ingestion resilient; `freeze` on tables stops a renamed endpoint
# silently creating a parallel table nobody models.
DEFAULT_CONTRACT = {"tables": "evolve", "columns": "evolve", "data_type": "freeze"}
STRICT_CONTRACT = {"tables": "freeze", "columns": "freeze", "data_type": "freeze"}


def build_pipeline(warehouse: Warehouse, source_name: str, dataset: str | None = None):
    """Create a dlt pipeline targeting the project's DuckDB file."""
    import dlt  # imported lazily so the platform works without the data extra

    return dlt.pipeline(
        pipeline_name=f"{warehouse.project}_{source_name}",
        destination=dlt.destinations.duckdb(str(warehouse.path)),
        dataset_name=dataset or source_name,
        progress=None,
    )


def run_source(
    warehouse: Warehouse,
    source: Any,
    source_name: str,
    dataset: str | None = None,
    contract: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run one annotated source and return a compact load summary."""
    # dlt opens the duckdb file directly rather than through `Warehouse.connect`,
    # so on a checkout that has never been seeded it fails in `_sync_destination`
    # with a DestinationConnectionError blaming credentials for a missing `data/`.
    warehouse.ensure_dir()
    pipeline = build_pipeline(warehouse, source_name, dataset)
    info = pipeline.run(source, schema_contract=contract or DEFAULT_CONTRACT)
    return {
        "pipeline": pipeline.pipeline_name,
        "dataset": pipeline.dataset_name,
        "load_ids": list(getattr(info, "loads_ids", []) or []),
        "destination": "duckdb",
    }


def export_project_annotations(project_dir: str | Path) -> Path:
    """Write contracts/annotations.yaml from every annotation registered by import."""
    return export_annotations(Path(project_dir) / "contracts" / "annotations.yaml")


def collect_sources(module: Any) -> dict[str, Any]:
    """Return every dlt resource/source in a module that carries an annotation."""
    out: dict[str, Any] = {}
    for name in dir(module):
        obj = getattr(module, name)
        if getattr(obj, "__pf_annotation__", None) is not None:
            out[getattr(obj, "name", name)] = obj
    return out


def monitors_for(annotations: Iterable[Any]) -> list[dict[str, Any]]:
    """Generate statistical monitors from ontology roles.

    This is what catches "revenue is 30% below the same weekday last month" —
    the failure dbt's deterministic tests never see.
    """
    monitors: list[dict[str, Any]] = []
    for ann in annotations:
        for col, role in ann.roles.items():
            match role:
                case "event_time":
                    monitors.append({"resource": ann.resource, "column": col,
                                     "kind": "freshness", "params": {"max_lag_hours": 26}})
                case "money_amount":
                    monitors.append({"resource": ann.resource, "column": col,
                                     "kind": "sum_drift",
                                     "params": {"baseline_weeks": 4, "tolerance_pct": 30}})
                case "status_enum":
                    monitors.append({"resource": ann.resource, "column": col,
                                     "kind": "category_drift", "params": {"alert_on_new": True}})
                case "natural_key" | "surrogate_key":
                    monitors.append({"resource": ann.resource, "column": col,
                                     "kind": "row_count_band",
                                     "params": {"baseline_days": 14, "tolerance_pct": 40}})
    return monitors
