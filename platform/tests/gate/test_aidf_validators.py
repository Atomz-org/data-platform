"""The model boundary: strict contracts, read-only SQL, no PII.

  strict means strict          a number as a string, an unknown field, a mart
                                 outside the entity's pattern — each is a
                                 rejection, never a coercion

  read-only means parsed       DDL, DML, a second statement, a system catalogue,
                                 a file-reading function and SELECT * are all
                                 refused by the AST, not by a regex; COUNT(*)
                                 and an alias are not false positives

  the catalogue is the truth   a column the mart does not have is a
                                 hallucination whatever it is called

  a finding never leaks        the PII scrubber reports the kind and the
                                 offset, never the value it found
"""

from __future__ import annotations

import json

import pytest
from pf.aidf.schemas import (
    AggregationType,
    MartMetricContract,
    SemanticModelContract,
    json_schema,
    validate_payload,
)
from pf.aidf.validators import PiiScrubber, SqlAstValidator
from pydantic import ValidationError

GOOD = {
    "mart_name": "fct_orders",
    "metric_name": "gross_revenue",
    "aggregation_type": "SUM",
    "sql_definition": "SELECT SUM(amount) AS gross_revenue FROM fct_orders WHERE status = 'paid'",
    "dependent_columns": ["amount", "status"],
    "author_agent": "metric-gap-harvester",
}


# ---------------------------------------------------------------- schema --

def test_good_payload_validates_and_canonicalises() -> None:
    m = validate_payload("mart_metric", GOOD)
    assert isinstance(m, MartMetricContract)
    assert m.aggregation_type is AggregationType.SUM
    c = m.canonical()
    assert c["status"] == "provisional" and c["created_at_utc"].endswith("Z")
    assert not any(isinstance(v, float) for v in c.values()), "no floats: the ledger refuses them"


@pytest.mark.parametrize("bad", [
    {**GOOD, "aggregation_type": "sum"},                      # case is meaning in strict mode
    {**GOOD, "dependent_columns": "amount"},                  # a string is not a list
    {**GOOD, "override_gate": True},                          # unknown field
    {**GOOD, "metric_name": "Gross Revenue"},                 # not snake_case
    {**GOOD, "sql_definition": "x"},                          # too short to be a definition
    {**GOOD, "dependent_columns": []},                        # must name what it reads
    {**GOOD, "dependent_columns": ["amount", "AMOUNT"]},      # repeats a column
    {**GOOD, "author_agent": "bad agent!"},
    {**GOOD, "created_at_utc": "2026-01-01T00:00:00"},        # naive timestamp
    {**GOOD, "created_at_utc": "2026-01-01T00:00:00+02:00"},  # not UTC
])
def test_strictness(bad: dict) -> None:
    with pytest.raises(ValidationError):
        validate_payload("mart_metric", bad)


def test_json_string_and_dict_are_judged_alike() -> None:
    a = validate_payload("mart_metric", json.dumps(GOOD))
    b = validate_payload("mart_metric", GOOD)
    assert a.canonical() | {"created_at_utc": ""} == b.canonical() | {"created_at_utc": ""}
    with pytest.raises(ValidationError):
        validate_payload("mart_metric", json.dumps({**GOOD, "dependent_columns": ["amount", 1]}))


def test_mart_pattern_comes_from_the_entity() -> None:
    validate_payload("mart_metric", GOOD)  # the floor accepts any snake_case
    with pytest.raises(ValidationError, match="pattern"):
        validate_payload("mart_metric", GOOD, mart_pattern=r"^adv_[a-z0-9_]+$")
    validate_payload("mart_metric", {**GOOD, "mart_name": "adv_customer_health"}, mart_pattern=r"^adv_[a-z0-9_]+$")


def test_contract_is_frozen() -> None:
    m = validate_payload("mart_metric", GOOD)
    with pytest.raises(ValidationError):
        m.metric_name = "other"  # type: ignore[misc]


def test_semantic_model_contract() -> None:
    m = validate_payload("semantic_model", {
        "name": "orders", "mart_name": "fct_orders", "primary_entity": "order_id",
        "measures": [{"name": "revenue", "aggregation": "SUM", "expression": "amount"}],
        "dimensions": [{"name": "ordered_at", "type": "time", "time_granularity": "day"}],
        "author_agent": "platform_orchestrator",
    })
    assert isinstance(m, SemanticModelContract) and m.sql_fragments() == ["amount"]
    with pytest.raises(ValidationError):
        validate_payload("semantic_model", {"name": "orders", "mart_name": "fct_orders", "primary_entity": "id",
                                            "measures": [], "author_agent": "x"})


def test_json_schema_is_what_the_prompt_shows() -> None:
    s = json_schema("mart_metric")
    assert s["additionalProperties"] is False
    assert set(s["required"]) >= {"mart_name", "metric_name", "aggregation_type", "sql_definition",
                                  "dependent_columns", "author_agent"}


# --------------------------------------------------------------- SQL AST --
V = SqlAstValidator("duckdb")


@pytest.mark.parametrize("sql", [
    "SELECT SUM(amount) FROM fct_orders",
    "SELECT COUNT(*) AS n FROM fct_orders",
    "SUM(amount) / NULLIF(COUNT(DISTINCT customer_id), 0)",
    "WITH paid AS (SELECT amount FROM fct_orders WHERE status = 'paid') SELECT SUM(amount) FROM paid",
    "SELECT o.amount AS a FROM fct_orders o ORDER BY a",
])
def test_read_only_sql_passes(sql: str) -> None:
    v = V.validate(sql)
    assert v.ok, [f.message for f in v.findings]


@pytest.mark.parametrize("sql, code", [
    ("DROP TABLE fct_orders", "mutation"),
    ("DELETE FROM fct_orders WHERE 1=1", "mutation"),
    ("INSERT INTO fct_orders SELECT * FROM staging", "mutation"),
    ("UPDATE fct_orders SET amount = 0", "mutation"),
    ("CREATE TABLE x AS SELECT 1", "mutation"),
    ("ALTER TABLE fct_orders ADD COLUMN x INT", "mutation"),
    ("SELECT 1; DROP TABLE fct_orders", "multiple_statements"),
    ("SELECT * FROM fct_orders", "star_projection"),
    ("SELECT o.* FROM fct_orders o", "star_projection"),
    ("SELECT table_name FROM information_schema.tables", "system_schema"),
    ("SELECT relname FROM pg_catalog.pg_class", "system_schema"),
    ("SELECT amount FROM read_parquet('s3://bucket/x.parquet')", "forbidden_function"),
    ("SELECT getenv('AWS_SECRET_ACCESS_KEY')", "forbidden_function"),
    ("SELECT FROM WHERE", "syntax"),
    ("", "empty"),
])
def test_unsafe_sql_is_refused(sql: str, code: str) -> None:
    v = V.validate(sql)
    assert not v.ok
    assert code in {f.code for f in v.findings}, [f.to_dict() for f in v.findings]


def test_hallucinated_column_against_the_catalogue() -> None:
    v = SqlAstValidator("duckdb", allowed_columns={"amount", "status"})
    ok = v.validate("SELECT SUM(amount) FROM fct_orders WHERE status = 'paid'")
    assert ok.ok and ok.checked["catalog"] == "present" and ok.checked["columns_checked"] == 2
    bad = v.validate("SELECT SUM(customer_ltv) FROM fct_orders")
    assert not bad.ok and bad.findings[0].code == "hallucinated_column" and "customer_ltv" in bad.findings[0].message


def test_aliases_and_ctes_are_not_hallucinations() -> None:
    v = SqlAstValidator("duckdb", allowed_columns={"amount", "status"}, allowed_tables={"fct_orders"})
    sql = ("WITH paid AS (SELECT amount AS paid_amount FROM fct_orders WHERE status = 'paid') "
           "SELECT SUM(paid_amount) AS total FROM paid ORDER BY total")
    r = v.validate(sql)
    assert r.ok, [f.message for f in r.findings]


def test_hallucinated_table_against_the_catalogue() -> None:
    v = SqlAstValidator("duckdb", allowed_tables={"fct_orders"})
    r = v.validate("SELECT SUM(amount) FROM fct_refunds")
    assert not r.ok and r.findings[0].code == "hallucinated_table"


def test_no_catalogue_is_reported_not_passed_silently() -> None:
    r = V.validate("SELECT SUM(anything) FROM anywhere")
    assert r.ok and r.checked["catalog"] == "absent"


def test_dialect_is_honoured() -> None:
    # `QUALIFY` is Snowflake/BigQuery/DuckDB; T-SQL's TOP is not DuckDB.
    assert SqlAstValidator("tsql").validate("SELECT TOP 1 amount FROM fct_orders").ok
    assert SqlAstValidator("snowflake").validate("SELECT amount FROM fct_orders QUALIFY ROW_NUMBER() OVER (ORDER BY amount) = 1").ok


def test_referenced_columns() -> None:
    assert V.referenced_columns("SELECT SUM(amount) AS a FROM t WHERE status = 'x' ORDER BY a") == {"amount", "status"}


# ------------------------------------------------------------------- PII --
P = PiiScrubber()


@pytest.mark.parametrize("text, label", [
    ("contact ops@example.com for access", "email"),
    ("db host 10.42.0.17 port 5432", "ipv4"),
    ("api_key = 'sk_live_abcdefghijklmnop'", "generic_secret"),
    ("Authorization: Bearer abcdefghijklmnopqrstuvwxyz012345", "bearer"),
    ("AKIAIOSFODNN7EXAMPLE", "aws_access_key"),
    ("-----BEGIN RSA PRIVATE KEY-----", "private_key"),
    ("DE89 3704 0044 0532 0130 00", "iban"),
])
def test_pii_and_secrets_are_refused(text: str, label: str) -> None:
    v = P.validate(text)
    assert not v.ok and v.findings[0].code == label


def test_finding_never_echoes_the_value() -> None:
    v = P.validate("password = 'hunter2hunter2'")
    assert not v.ok
    assert "hunter2" not in v.findings[0].message
    assert "offset" in v.findings[0].message


@pytest.mark.parametrize("text", [
    "SELECT SUM(amount) FROM fct_orders",
    "version 1.2.3 of the driver",
    "127.0.0.1 is loopback",
])
def test_ordinary_text_passes(text: str) -> None:
    v = P.validate(text)
    assert v.ok, [f.to_dict() for f in v.findings]


def test_allowlist_is_a_decision() -> None:
    assert not P.validate("owner: svc-metrics@example.com").ok
    assert PiiScrubber(allow=[r"svc-metrics@example\.com"]).validate("owner: svc-metrics@example.com").ok


def test_payload_scan_names_the_field() -> None:
    v = P.validate_payload({"rationale": "ask jo@example.com", "sql_definition": "SELECT 1", "nested": {"ip": "8.8.8.8"}})
    assert not v.ok
    assert {f.path for f in v.findings} == {"$.rationale", "$.nested.ip"}
    assert v.checked["fields"] == 3


def test_ipv4_pattern_rejects_out_of_range_octets() -> None:
    assert P.validate("999.999.999.999").ok
