"""dlt Core lands the raw stage; the platform owns the pipeline around it."""

from __future__ import annotations

from pathlib import Path

import dlt
import pytest
from pf.ontology import annotate
from pf.ontology.annotate import registry
from pf.runtime.dlt_runtime import run_source
from pf.runtime.warehouse import Warehouse


@pytest.fixture()
def dlt_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pipeline state under the test, not under ~/.dlt."""
    home = tmp_path / "dlt"
    monkeypatch.setenv("DLT_DATA_DIR", str(home))
    return home


def test_run_source_reports_what_is_there(tmp_path: Path, dlt_home: Path) -> None:
    """The summary counts rows in the dataset, so a seed can refuse to build
    marts over a table that a green load left empty."""
    wh = Warehouse(group="g", project="p", path=tmp_path / "data" / "p.duckdb")

    @dlt.resource(name="orders", primary_key="id", write_disposition="merge")
    def orders():
        yield [{"id": 1, "qty": 2}, {"id": 2, "qty": 5}]

    info = run_source(wh, orders(), source_name="shop")
    assert info["dataset"] == "shop" and info["rows"] == {"orders": 2}
    assert run_source(wh, orders(), source_name="shop")["rows"] == {"orders": 2}  # merged


def test_annotate_applies_to_a_resource_dlt_generated(dlt_home: Path) -> None:
    """A rest_api resource has no function to decorate. `annotate(...)(resource)`
    must register it and hint its columns exactly as the decorator does."""
    from dlt.sources.rest_api import rest_api_resources

    parent = dlt.resource(lambda: iter([[{"k": "a"}]]), name="keys", selected=False)
    [child] = [r for r in rest_api_resources({
        "client": {"base_url": "https://example.invalid/"},
        "resources": [parent, {"name": "things", "endpoint": {
            "path": "things/{k}",
            "params": {"k": {"type": "resolve", "resource": "keys", "field": "k"}}}}],
    }) if r.name == "things"]
    annotate(source="ex", concept="Thing", roles={"k": "natural_key"})(child)
    assert registry()["things"].source == "ex"
    assert child.columns["k"]["x-role"] == "natural_key"
    assert child.__pf_annotation__.concept == "Thing"
