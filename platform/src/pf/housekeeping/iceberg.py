"""Iceberg-on-R2 housekeeping — observed, because the catalog owns the work.

The inversion of DuckLake, and the module encodes it rather than hiding it.
R2 Data Catalog rewrites small files itself once managed compaction is
enabled on the catalog; snapshot expiry is not offered yet; and the DuckDB
connection this platform holds can CREATE and INSERT but not DELETE — so a
task here that claimed to compact or expire would be a lie that fails at
runtime. What the platform *can* do is see: which tables are fragmenting,
which are accumulating snapshots, and say precisely what to enable (managed
compaction, per catalog) or run elsewhere (expiry, from an engine with
delete rights) — with the numbers that justify the trip.

Metadata reads are best-effort per table. The iceberg extension's metadata
functions vary by DuckDB version in how they address attached-catalog tables,
and a housekeeping report that dies on table 3 of 40 tells you less than one
that says "37 inspected, 3 unreadable".
"""

from __future__ import annotations

import os

from pf.housekeeping.core import Task

CATALOG = "lake"

#: Snapshot count past which a table earns a line in the expiry task. Every
#: dbt rebuild commits once per table, so daily builds cross this in ~2 months.
SNAPSHOT_ALERT = int(os.environ.get("PF_HOUSEKEEPING_SNAPSHOT_ALERT", "50"))


def connect():
    """Attach R2 Data Catalog exactly as the prod target does."""
    import duckdb

    missing = [v for v in ("R2_CATALOG_WAREHOUSE", "R2_CATALOG_ENDPOINT",
                           "R2_CATALOG_TOKEN") if not os.environ.get(v)]
    if missing:
        raise RuntimeError(
            f"{', '.join(missing)} not set — housekeeping attaches the same "
            f"catalog the prod target names, and refuses to guess it.")
    token = os.environ["R2_CATALOG_TOKEN"].replace("'", "''")
    warehouse = os.environ["R2_CATALOG_WAREHOUSE"].replace("'", "''")
    endpoint = os.environ["R2_CATALOG_ENDPOINT"].replace("'", "''")
    con = duckdb.connect()
    con.execute("INSTALL iceberg; LOAD iceberg;")
    con.execute(f"CREATE SECRET r2_catalog (TYPE iceberg, TOKEN '{token}')")
    con.execute(f"ATTACH '{warehouse}' AS {CATALOG} (TYPE iceberg, ENDPOINT '{endpoint}')")
    return con


def inspect(con) -> tuple[list[dict], list[str]]:
    """Tables in the catalog, with snapshot counts where DuckDB can read them."""
    import duckdb

    rows = con.execute(
        "SELECT schema_name, table_name FROM duckdb_tables() "
        "WHERE database_name = ? ORDER BY 1, 2", [CATALOG]).fetchall()
    tables: list[dict] = []
    unreadable = 0
    for schema, table in rows:
        entry: dict = {"table": f"{schema}.{table}", "snapshots": None}
        try:
            entry["snapshots"] = int(con.execute(
                f"SELECT count(*) FROM iceberg_snapshots('{CATALOG}.{schema}.{table}')"
            ).fetchone()[0])
        except duckdb.Error:
            unreadable += 1
        tables.append(entry)
    notes = [f"{len(tables)} table(s) in the catalog"]
    if unreadable:
        notes.append(f"{unreadable} table(s) unreadable via iceberg_snapshots() "
                     f"on this DuckDB version — counts shown where available")
    return tables, notes


def plan(tables: list[dict], days: int) -> list[Task]:
    """What to enable and where — nothing here executes against the catalog."""
    bucket = os.environ.get("R2_CATALOG_WAREHOUSE", "<account>_<bucket>")
    bucket_name = bucket.split("_", 1)[-1]
    tasks = [Task(
        name="managed_compaction",
        reason="every dbt rebuild is one small-file commit per table; "
               "compaction is what keeps scans flat and it is off by default",
        manual=(f"verify it is enabled on the catalog: R2 → {bucket_name} → "
                f"Settings → Data Catalog, or "
                f"`npx wrangler r2 bucket catalog compaction enable {bucket_name}`"),
    )]
    growing = sorted(t["table"] for t in tables
                     if t.get("snapshots") and t["snapshots"] > SNAPSHOT_ALERT)
    if growing:
        tasks.append(Task(
            name="expire_snapshots",
            reason=(f"{len(growing)} table(s) past {SNAPSHOT_ALERT} snapshots "
                    f"({', '.join(growing[:5])}{'…' if len(growing) > 5 else ''}); "
                    f"retention target is {days} day(s)"),
            manual=("R2 Data Catalog does not expire snapshots yet and this "
                    "platform's DuckDB connection has no delete capability — "
                    "run expiry from an engine that does (PyIceberg or Spark "
                    "against the same REST endpoint) until managed expiry ships."),
        ))
    return tasks
