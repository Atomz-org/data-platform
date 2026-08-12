"""Cross-entity roll-up. Attaches every sister warehouse READ_ONLY.

This is the only place in the platform that reads more than one entity. It works
because sisters share the group ontology, so `fct_revenue` has the same grain and
semantics in both — the union is safe by construction, not by convention.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from pf import obs                                    # noqa: E402
from pf.runtime.warehouse import Warehouse            # noqa: E402

GROUP = "acme"
PROJECT = "acme-rollup"
SISTERS = {
    "us": PROJECT_DIR.parent / "acme-us" / "data" / "acme_us.duckdb",
    "eu": PROJECT_DIR.parent / "acme-eu" / "data" / "acme_eu.duckdb",
}


def main() -> int:
    wh = Warehouse.for_project(PROJECT_DIR, GROUP, PROJECT)
    missing = [a for a, p in SISTERS.items() if not p.exists()]
    if missing:
        print(f"  sisters not seeded yet: {', '.join(missing)}")
        return 1

    t0 = time.time()
    with wh.attach_sisters(SISTERS) as con:
        union = " UNION ALL ".join(
            f"SELECT '{alias.upper()}' AS entity, * FROM {alias}.main_marts.fct_revenue"
            for alias in SISTERS
        )
        con.execute(f"CREATE OR REPLACE TABLE group_revenue AS {union}")
        rows, entities = con.execute(
            "SELECT count(*), count(DISTINCT entity) FROM group_revenue").fetchone()
        by_entity = con.execute(
            "SELECT entity, currency_code, round(sum(net_amount), 2) net, count(*) AS day_buckets "
            "FROM group_revenue GROUP BY 1, 2 ORDER BY 1"
        ).fetchall()

    obs.record_pipeline_run(group=GROUP, project=PROJECT, kind="rollup",
                            name="group_revenue", status="ok", rows=rows,
                            duration_ms=int((time.time() - t0) * 1000),
                            message=f"{entities} entities attached READ_ONLY")
    print(f"  rollup → group_revenue ({rows:,} rows across {entities} entities)")
    for entity, ccy, net, days in by_entity:
        print(f"    {entity}  {net:>12,.2f} {ccy}  over {days} day-buckets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
