"""Publish the MCX trading vocabulary and report lineage to OpenMetadata.

`pf tool openmetadata publish` already sends what the ontology declares — the
classes (ExchangeContract, ContractSession, ...) as glossary terms, the roles
as tags, the MetricFlow metrics — and `catalog/ingestion/dbt.yaml` ingests dbt's
manifest, catalog and run results for structural lineage. This adds what
neither can derive:

  * a **Commodities Ontology** glossary: the segments MCX trades in (Bullion,
    Energy, Base Metals, ...), each commodity under its segment with its MCX
    codes as synonyms, and the trading concepts the marts compute (Contango,
    Roll Yield, Garman–Klass Volatility, Max Pain, OI Build-up, ...);
  * a **Tier** classification on the MCX tables — Tier1 for the marts and the
    board a person reads, Tier2 for raw and intermediate;
  * the glossary terms on the columns that carry them;
  * **lineage from each dbt model to the Evidence page that reads it**, taken
    from the dbt exposures `pf report build` writes, as `AddLineageRequest`
    edges — so a trader who doubts a Garman–Klass spike on /mcx/gold can walk
    it back to `fct_mcx_commodity_daily` and the dlt table under it.

Standard library only — no SDK. The OpenMetadata SDK pins antlr4 below what
Dagster needs, so the repo keeps it out of the workspace, and its generated
classes move between releases; the REST calls underneath do not.

    python catalog/mcx_ontology.py                       # print the payload
    OPENMETADATA_JWT_TOKEN=... python catalog/mcx_ontology.py --apply
      # OPENMETADATA_HOST_PORT defaults to http://localhost:8585/api

It also creates what the lineage needs endpoints for: the Evidence pages as
dashboards (`commodity_india_evidence`) and each commodity's Dagster job as a
pipeline (`commodity_india_dagster`) feeding the raw MCX tables.

Every call is create-or-update, so re-running is idempotent.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[1]
SEED = PROJECT_DIR / "transform" / "seeds" / "mcx_products.csv"
MANIFEST = PROJECT_DIR / "transform" / "target" / "manifest.json"
SERVICE = "commodity_commodity_india"            # catalog/ingestion/*.yaml serviceName
DATABASE = "commodity_india"
DASHBOARD_SERVICE = "commodity_india_evidence"
PIPELINE_SERVICE = "commodity_india_dagster"
GLOSSARY = "Commodities Ontology"

SEGMENTS = {
    "bullion": ("Precious Metals", ("Gold and silver: quoted per gram or kilogram, driven by "
                "the dollar, real rates and import duty.")),
    "energy": ("Energy", ("Crude oil and natural gas: quoted per barrel and per mmBtu, "
               "tracking NYMEX with a rupee overlay.")),
    "power": ("Power", "Electricity futures, per MWh, on the Indian power exchanges' prices."),
    "base_metal": ("Base Metals", ("Copper, aluminium, zinc, lead and nickel: quoted per kg, "
                   "tracking the LME.")),
    "ferrous": ("Ferrous", "Steel products, per tonne."),
    "agri": ("Agricultural Commodities", ("Cardamom, mentha oil, cotton and kapas: domestic "
             "spot-driven contracts.")),
}

#: Trading concepts the marts compute: (term, definition, the columns that carry it).
CONCEPTS: list[tuple[str, str, list[str]]] = [
    ("Contango", ("Deferred futures dearer than the near month; a long pays to roll. "
     "is_contango in fct_mcx_commodity_daily."),
     ["fct_mcx_commodity_daily.is_contango", "rpt_mcx_commodity_board.is_contango"]),
    ("Backwardation", "Near month dearer than deferred; a long earns on the roll.",
     ["fct_mcx_commodity_daily.is_backwardation", "rpt_mcx_commodity_board.is_backwardation"]),
    ("Roll Yield", ("(near ÷ next − 1) × 365 ÷ days between expiries: what a long earns "
     "rolling near into next, annualised. Negative in contango."),
     ["fct_mcx_commodity_daily.roll_yield_annualised", "rpt_mcx_commodity_board.roll_yield_annualised"]),
    ("Garman-Klass Volatility", ("Garman & Klass (1980) OHLC range estimator, "
     "σ² = 0.511(u−d)² − 0.019[k(u+d) − 2ud] − 0.383k² with u=ln H/O, d=ln L/O, k=ln C/O; "
     "averaged over 14/30/90 sessions, annualised on 252."),
     [f"fct_mcx_commodity_daily.garman_klass_vol_{n}d" for n in (14, 30, 90)]
     + ["rpt_mcx_commodity_board.garman_klass_vol_30d"]),
    ("Parkinson Volatility", "Parkinson (1980) high-low estimator, (ln H/L)² ÷ 4 ln 2.",
     [f"fct_mcx_commodity_daily.parkinson_vol_{n}d" for n in (14, 30, 90)]),
    ("Rogers-Satchell Volatility", ("Rogers & Satchell (1991) drift-robust estimator, "
     "u(u−k) + d(d−k)."),
     [f"fct_mcx_commodity_daily.rogers_satchell_vol_{n}d" for n in (14, 30, 90)]),
    ("Exponential Moving Average", ("Recursive EMA with α = 2/(n+1), n = 9, 12, 21, 26, 200, "
     "on the roll-free continuous series."),
     [f"fct_mcx_commodity_daily.ema_{n}" for n in (9, 12, 21, 26, 200)]),
    ("Relative Strength Index", "Wilder RSI(14): 100 − 100/(1 + avg gain ÷ avg loss), α = 1/14.",
     ["fct_mcx_commodity_daily.rsi_14"]),
    ("Open Interest Build-up", ("Price and OI change read together: long build-up, short "
     "build-up, short covering, long unwinding."),
     ["fct_mcx_commodity_daily.oi_buildup", "fct_mcx_futures_daily.oi_buildup"]),
    ("Put-Call Ratio", "Put open interest (or volume) over call, per option expiry.",
     ["fct_mcx_options_daily.put_call_ratio_oi", "fct_mcx_options_daily.put_call_ratio_volume"]),
    ("Max Pain", "The settlement strike at which option holders would be paid least.",
     ["fct_mcx_options_daily.max_pain_strike"]),
    ("Import Parity Premium", ("MCX settlement over the landed import-parity price "
     "(benchmark × USD/INR × (1 + duty)) for the same quote basis, minus one."),
     ["fct_mcx_commodity_daily.premium_to_landed_pct"]),
]

TIER1 = ("fct_mcx_commodity_daily", "fct_mcx_futures_daily", "fct_mcx_options_daily",
         "dim_mcx_contracts", "rpt_mcx_commodity_board")


def _commodities() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    with SEED.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            c = out.setdefault(r["mcx_commodity"], {"segment": r["segment"], "codes": []})
            c["codes"].append(r["contract_code"])
    return out


def _mcx_models(manifest: dict[str, Any]) -> dict[str, str]:
    """dbt model name → schema, for every MCX model in the manifest."""
    return {n["name"]: n["schema"] for n in manifest.get("nodes", {}).values()
            if n.get("resource_type") == "model" and "mcx" in n["name"]}


def _report_edges(manifest: dict[str, Any], models: dict[str, str]) -> list[dict[str, str]]:
    """(dbt model → Evidence page) from the exposures `pf report build` writes."""
    edges = []
    for exp in manifest.get("exposures", {}).values():
        for dep in exp.get("depends_on", {}).get("nodes", []):
            name = dep.split(".")[-1]
            if name in models:
                edges.append({"model": name, "schema": models[name], "page": exp["name"],
                              "label": exp.get("label") or exp["name"], "url": exp.get("url") or ""})
    return edges


def build_payload() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    models = _mcx_models(manifest)
    segments, commodity_terms = [], []
    for label, desc in SEGMENTS.values():
        segments.append({"name": label, "description": desc})
    for name, c in _commodities().items():
        seg_label = SEGMENTS.get(c["segment"], (c["segment"].title(), ""))[0]
        commodity_terms.append({
            "key": name,
            "name": name.replace("_", " ").title(), "parent": seg_label,
            "description": f"MCX {name.replace('_', ' ')}: contracts {', '.join(c['codes'])}. "
                           f"Report: /mcx/{name}.",
            "synonyms": c["codes"]})
    fqn = lambda m, col=None: ".".join(  # noqa: E731
        [SERVICE, DATABASE, models.get(m, "main_marts"), m] + ([col] if col else []))
    return {
        "glossary": {"name": GLOSSARY, "description": "What MCX trades and how a desk reads it. "
                     "Published by catalog/mcx_ontology.py from the mcx_products seed."},
        "segments": segments,
        "commodities": commodity_terms,
        "concepts": [{"name": n, "description": d,
                      "columns": [fqn(*c.split(".")) for c in cols if c.split(".")[0] in models]}
                     for n, d, cols in CONCEPTS],
        "tiers": {fqn(m): ("Tier.Tier1" if m in TIER1 else "Tier.Tier2") for m in models},
        "lineage": [{**e, "table": fqn(e["model"])} for e in _report_edges(manifest, models)],
    }


class OM:
    """The handful of OpenMetadata REST calls this needs, over the standard library.

    REST rather than the SDK's generated classes: those move between releases
    (1.12 → 1.13 renamed half the lineage models), and this script is meant to
    keep working against whatever server the catalogue runs. Every write is a
    PUT, which OpenMetadata treats as create-or-update, so a re-run is a no-op.
    """

    def __init__(self, host: str, token: str) -> None:
        self.host = host.rstrip("/")
        self.token = token

    def call(self, method: str, path: str, body: Any = None,
             content_type: str = "application/json") -> Any:
        import urllib.error
        import urllib.request

        req = urllib.request.Request(
            f"{self.host}/v1/{path.lstrip('/')}", method=method,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": content_type})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404 and method == "GET":
                return None
            raise RuntimeError(f"{method} {path}: HTTP {exc.code} {exc.read()[:300]!r}") from exc
        return json.loads(raw) if raw else None

    def put(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return self.call("PUT", path, body)

    def get_by_name(self, kind: str, fqn: str, fields: str = "") -> dict[str, Any] | None:
        from urllib.parse import quote
        q = f"?fields={fields}" if fields else ""
        return self.call("GET", f"{kind}/name/{quote(fqn, safe='')}{q}")

    def patch(self, kind: str, entity_id: str, ops: list[dict[str, Any]]) -> None:
        if ops:
            self.call("PATCH", f"{kind}/{entity_id}", ops, "application/json-patch+json")


def _add_tag_ops(tags: list[dict[str, Any]], fqn: str, source: str, pointer: str) -> list[dict[str, Any]]:
    if any(tg.get("tagFQN") == fqn for tg in tags or []):
        return []
    return [{"op": "add", "path": f"{pointer}/-",
             "value": {"tagFQN": fqn, "source": source, "labelType": "Manual", "state": "Confirmed"}}]


def _page_url(rel: str) -> str:
    """`reporting/pages/mcx/[commodity].md` → the served page (gold as the example)."""
    if not rel.startswith("reporting/pages/"):
        return "http://localhost:4789/"
    path = rel.removeprefix("reporting/pages/").removesuffix(".md").removesuffix("index")
    return "http://localhost:4789/" + path.replace("[commodity]", "gold")


def safe_name(name: str) -> str:
    """OpenMetadata entity names: no brackets (`report_mcx_[commodity]`)."""
    return name.replace("[", "").replace("]", "")


def apply(payload: dict[str, Any]) -> dict[str, int]:  # pragma: no cover — needs a server
    """Create-or-update everything in the payload; returns counts per kind."""
    om = OM(os.environ.get("OPENMETADATA_HOST_PORT", "http://localhost:8585/api"),
            os.environ["OPENMETADATA_JWT_TOKEN"])
    sent: dict[str, int] = {}

    def count(kind: str) -> None:
        sent[kind] = sent.get(kind, 0) + 1

    g = payload["glossary"]
    glossary = om.put("glossaries", {"name": g["name"], "displayName": g["name"],
                                     "description": g["description"]})
    gname = glossary["fullyQualifiedName"]

    def term(name: str, description: str, parent: str | None = None,
             synonyms: list[str] | None = None) -> dict[str, Any]:
        body = {"glossary": gname, "name": name, "displayName": name,
                "description": description, "synonyms": synonyms or []}
        if parent:
            body["parent"] = f"{gname}.{parent}"
        count("glossary terms")
        return om.put("glossaryTerms", body)

    for s in payload["segments"]:
        term(s["name"], s["description"])
    for c in payload["commodities"]:
        term(c["name"], c["description"], parent=c["parent"], synonyms=c["synonyms"])

    for concept in payload["concepts"]:
        t = term(concept["name"], concept["description"])
        for col_fqn in concept["columns"]:
            table_fqn, column = col_fqn.rsplit(".", 1)
            table = om.get_by_name("tables", table_fqn, "columns,tags")
            if table is None:
                print(f"  skip {col_fqn}: table not in the catalogue yet")
                continue
            idx = next((i for i, c in enumerate(table["columns"]) if c["name"] == column), None)
            if idx is None:
                continue
            om.patch("tables", table["id"], _add_tag_ops(
                table["columns"][idx].get("tags"), t["fullyQualifiedName"], "Glossary",
                f"/columns/{idx}/tags"))
            count("column terms")

    for table_fqn, tier in payload["tiers"].items():
        table = om.get_by_name("tables", table_fqn, "tags")
        if table is not None:
            om.patch("tables", table["id"], _add_tag_ops(table.get("tags"), tier, "Classification", "/tags"))
            count("tier tags")

    # Evidence pages as dashboards, so lineage has somewhere to end.
    om.put("services/dashboardServices", {
        "name": DASHBOARD_SERVICE, "serviceType": "CustomDashboard",
        "description": "Evidence BI pages of commodity-india (reporting/pages), published by catalog/mcx_ontology.py.",
        "connection": {"config": {"type": "CustomDashboard"}}})
    pages: dict[str, dict[str, Any]] = {}
    for e in payload["lineage"]:
        name = safe_name(e["page"])
        if name not in pages:
            pages[name] = om.put("dashboards", {
                "name": name, "displayName": e["label"], "service": DASHBOARD_SERVICE,
                "sourceUrl": _page_url(e["url"]),
                "description": f"Evidence page `{e['url']}`." if e["url"] else "Declared dbt exposure."})
            count("dashboards")
        table = om.get_by_name("tables", e["table"])
        if table is None:
            continue
        om.put("lineage", {"edge": {
            "fromEntity": {"id": table["id"], "type": "table"},
            "toEntity": {"id": pages[name]["id"], "type": "dashboard"},
            "lineageDetails": {"description": f"Evidence page {e['url']} reads {e['model']}"}}})
        count("table → dashboard lineage")

    # Each commodity's Dagster job, feeding the raw MCX tables.
    om.put("services/pipelineServices", {
        "name": PIPELINE_SERVICE, "serviceType": "CustomPipeline",
        "description": "Dagster jobs of commodity-india: one per MCX commodity (dlt → dbt → Evidence).",
        "connection": {"config": {"type": "CustomPipeline"}}})
    raw = [om.get_by_name("tables", f"{SERVICE}.{DATABASE}.mcx.{t}")
           for t in ("futures_bhavcopy", "options_bhavcopy", "contract_master")]
    for c in payload["commodities"]:
        job = f"mcx_{c['key']}_ingest"
        pipe = om.put("pipelines", {
            "name": job, "displayName": f"MCX {c['name']} — dlt → dbt → Evidence",
            "service": PIPELINE_SERVICE,
            "sourceUrl": f"http://127.0.0.1:3070/locations/commodity__commodity-india/jobs/{job}",
            "description": c["description"],
            "tasks": [{"name": "load", "displayName": f"dlt: mcx_{c['key']}"},
                      {"name": "verify", "displayName": "mcx_landed_tables"},
                      {"name": "dbt", "displayName": "dbt build (tag:mcx)"},
                      {"name": "report", "displayName": "evidence build"}]})
        count("pipelines")
        for table in raw:
            if table is not None:
                om.put("lineage", {"edge": {
                    "fromEntity": {"id": pipe["id"], "type": "pipeline"},
                    "toEntity": {"id": table["id"], "type": "table"},
                    "lineageDetails": {"description": f"{job} lands MCX {c['name']} here"}}})
                count("pipeline → table lineage")
    return sent


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--apply", action="store_true", help="publish to the OpenMetadata server")
    args = ap.parse_args(argv)
    payload = build_payload()
    if args.apply:
        for kind, n in apply(payload).items():
            print(f"  ↑ {kind}: {n}")
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
