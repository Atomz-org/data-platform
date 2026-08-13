"""Induce a candidate ontology from a scanned data source.

Modelled on the Scan → Model → Serve shape of AWS's context-ontology-accelerator.
This module is Scan and the first half of Model: it looks at what a dlt source
actually landed and proposes classes, properties and relations. It never applies
them — induction produces a **proposal**, and a proposal is reviewed by a human
before it becomes vocabulary.

That boundary is the point. An ontology that a machine can silently extend is not
a shared vocabulary, it is a log of whatever schemas happened to arrive. The value
of the term `Customer` is that everyone means the same thing by it, and only a
person can decide that a newly-scanned `accounts` table is one.

Every proposed axiom therefore carries:

    evidence     the observation that suggested it (a name, a type, a statistic)
    confidence   high / medium / low
    rationale    why the rule fired, in a sentence a steward can disagree with

Low-confidence and PII inferences are proposed but never pre-approved: a steward
has to say yes. Guessing that a column is a person's name and silently tagging it
is worse than not tagging it, because the tag then carries authority it did not earn.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

Confidence = Literal["high", "medium", "low"]

# Name patterns. Deliberately conservative: a false positive here becomes a term
# in a shared vocabulary, which is far more expensive than a missed one.
PII_PATTERNS = {
    "pii_email": re.compile(r"(^|_)(email|e_?mail)(_|$)", re.I),
    "pii_phone": re.compile(r"(^|_)(phone|mobile|msisdn|tel)(_|$)", re.I),
    "pii_name": re.compile(r"(^|_)(first_?name|last_?name|full_?name|surname)(_|$)", re.I),
    "pii_address": re.compile(r"(^|_)(address|street|postcode|zip)(_|$)", re.I),
}
MONEY = re.compile(r"(amount|price|total|revenue|cost|fee|balance|mrr|arr)", re.I)
CURRENCY = re.compile(r"(^|_)currency(_code)?(_|$)", re.I)
COUNTRY = re.compile(r"(^|_)(country|country_code|nation)(_|$)", re.I)
TIMEISH = re.compile(r"(_at$|_date$|_time$|^date$|^timestamp$|created|updated|occurred)", re.I)
QUANTITY = re.compile(r"(^|_)(qty|quantity|count|units|seats)(_|$)", re.I)
STATUSISH = re.compile(r"(status|state|type|kind|tier|plan|segment|channel|category)", re.I)

TYPE_MAP = {
    "VARCHAR": "string", "TEXT": "string", "BLOB": "string", "UUID": "string",
    "BIGINT": "integer", "INTEGER": "integer", "SMALLINT": "integer", "HUGEINT": "integer",
    "DECIMAL": "decimal", "NUMERIC": "decimal",
    "DOUBLE": "float", "FLOAT": "float", "REAL": "float",
    "BOOLEAN": "boolean",
    "TIMESTAMP": "timestamp", "TIMESTAMP WITH TIME ZONE": "timestamp",
    "DATE": "date", "TIME": "string",
}


@dataclass
class Axiom:
    """One proposed statement, with the observation behind it."""

    kind: Literal["class", "property", "relation", "identity"]
    subject: str
    payload: dict[str, Any]
    confidence: Confidence
    evidence: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "subject": self.subject, **self.payload,
                "confidence": self.confidence, "evidence": self.evidence,
                "rationale": self.rationale}


@dataclass
class ColumnProfile:
    name: str
    data_type: str
    rows: int = 0
    distinct: int = 0
    nulls: int = 0

    @property
    def datatype(self) -> str:
        base = self.data_type.upper().split("(")[0].strip()
        return TYPE_MAP.get(base, "string")

    @property
    def unique(self) -> bool:
        return self.rows > 0 and self.distinct == self.rows

    @property
    def not_null(self) -> bool:
        return self.nulls == 0

    @property
    def low_cardinality(self) -> bool:
        return 0 < self.distinct <= 25 and (self.rows == 0 or self.distinct < self.rows * 0.1)


@dataclass
class TableProfile:
    name: str
    schema: str
    rows: int
    columns: list[ColumnProfile] = field(default_factory=list)


# ------------------------------------------------------------------ scan ----
def scan(warehouse: Path, schema: str, sample_rows: int = 0) -> list[TableProfile]:
    """Profile every table in a schema: types, row counts, distinct counts, nulls.

    Statistics matter more than names here. A column called `customer_id` that is
    unique and not-null is a key; the same name with 3 distinct values across
    1,800 rows is a foreign key. The name alone cannot tell them apart.
    """
    import duckdb

    if not warehouse.exists():
        return []
    con = duckdb.connect(str(warehouse), read_only=True)
    try:
        tables = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = ? ORDER BY 1", [schema]).fetchall()
        out: list[TableProfile] = []
        for (table,) in tables:
            if table.startswith("_dlt"):
                continue
            cols = con.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position",
                [schema, table]).fetchall()
            rows = con.execute(f'SELECT count(*) FROM "{schema}"."{table}"').fetchone()[0]
            profiles = []
            for name, dtype in cols:
                if name.startswith("_dlt"):
                    continue
                try:
                    d, n = con.execute(
                        f'SELECT count(DISTINCT "{name}"), count(*) - count("{name}") '
                        f'FROM "{schema}"."{table}"').fetchone()
                except Exception:
                    d, n = 0, 0
                profiles.append(ColumnProfile(name, dtype, rows, d or 0, n or 0))
            out.append(TableProfile(table, schema, rows, profiles))
        return out
    finally:
        con.close()


# ----------------------------------------------------------------- model ----
def _class_name(table: str) -> str:
    """Table -> singular PascalCase class name."""
    stem = re.sub(r"^(dim|fct|stg|raw)_+", "", table)
    stem = re.sub(r"_+", " ", stem).strip()
    words = [w for w in stem.split() if w]
    singular = []
    for w in words:
        if w.endswith("ies"):
            w = w[:-3] + "y"
        elif w.endswith("sses") or w.endswith("shes") or w.endswith("ches"):
            w = w[:-2]
        elif w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        singular.append(w.capitalize())
    return "".join(singular) or table.capitalize()


def _role_for(col: ColumnProfile, table_key: str | None) -> tuple[str, Confidence, str, str]:
    """(role, confidence, evidence, rationale) for one column."""
    n = col.name

    for role, pattern in PII_PATTERNS.items():
        if pattern.search(n):
            return (role, "medium", f"column name matches /{pattern.pattern}/",
                    "Name suggests personal data. Proposed, never auto-applied — a "
                    "wrong PII tag carries authority it did not earn, and a missing "
                    "one fails the mart policy loudly.")

    if col.name == table_key:
        return ("natural_key", "high",
                f"unique={col.unique}, not_null={col.not_null}, rows={col.rows}",
                "Unique and not-null across every row: this identifies the entity.")

    if n.endswith("_id") or n == "id":
        return ("foreign_key", "high",
                f"name ends in _id, distinct={col.distinct} of {col.rows} rows",
                "Repeats across rows, so it points at another entity rather than "
                "identifying this one.")

    if CURRENCY.search(n):
        return ("currency_code", "high", "name matches /currency/",
                "Qualifies a monetary amount; the money policy requires the pair.")

    if MONEY.search(n) and col.datatype in ("decimal", "float", "integer"):
        return ("money_amount", "high", f"name matches /amount|price|total|…/ and type {col.data_type}",
                "Numeric and named for money. Requires a sibling currency_code.")

    if col.datatype in ("timestamp", "date") or TIMEISH.search(n):
        if col.datatype in ("timestamp", "date"):
            return ("event_time", "high", f"type {col.data_type}",
                    "Temporal column: candidate aggregation time dimension for metrics.")
        return ("event_time", "low", f"name matches /_at|_date|…/ but type is {col.data_type}",
                "Named like a time but not typed as one — likely needs a cast in staging.")

    if COUNTRY.search(n):
        return ("geo_country", "medium", "name matches /country/", "Geographic dimension.")

    if QUANTITY.search(n) and col.datatype == "integer":
        return ("quantity", "medium", f"name matches /qty|count|…/ and type {col.data_type}",
                "Countable measure.")

    if col.datatype == "string" and col.low_cardinality and STATUSISH.search(n):
        return ("status_enum", "high",
                f"{col.distinct} distinct values over {col.rows} rows",
                "Low cardinality and named for a lifecycle state: a dimension, and a "
                "candidate for category-drift monitoring.")

    if col.datatype == "string" and col.low_cardinality:
        return ("status_enum", "medium", f"{col.distinct} distinct values over {col.rows} rows",
                "Low cardinality suggests a dimension rather than free text.")

    if col.datatype == "string":
        return ("free_text", "low", "string with high cardinality",
                "Defaulted to free text; never becomes a dimension.")

    return ("", "low", f"type {col.data_type}", "No rule matched; left unroled for the steward.")


def _identity_of(table: TableProfile) -> str | None:
    """The column that identifies a row: unique, not-null, id-shaped."""
    candidates = [c for c in table.columns if c.unique and c.not_null]
    if not candidates:
        return None
    for c in candidates:
        if c.name == "id" or c.name.endswith("_id"):
            return c.name
    return candidates[0].name


def induce(tables: list[TableProfile], known_classes: set[str]) -> list[Axiom]:
    """Turn profiles into proposed axioms."""
    axioms: list[Axiom] = []
    identities: dict[str, tuple[str, str]] = {}   # class -> (table, id column)

    for table in tables:
        cls = _class_name(table.name)
        key = _identity_of(table)
        identities[cls] = (table.name, key or "")

        if cls in known_classes:
            axioms.append(Axiom(
                "class", cls, {"action": "reuse", "table": table.name},
                "high", f"`{cls}` already exists in the ontology",
                "Reusing a term rather than minting a synonym is the whole point of "
                "a shared vocabulary. Verify the meaning matches before approving."))
        else:
            axioms.append(Axiom(
                "class", cls,
                {"action": "add", "table": table.name, "rows": table.rows,
                 "identity": key, "parent": None},
                "high" if key else "medium",
                f"table `{table.schema}.{table.name}` with {table.rows:,} rows",
                "A table at a consistent grain proposes an entity. Set `parent` if it "
                "specialises an existing class — that is a judgement only you can make."))

        if key:
            already = cls in known_classes
            axioms.append(Axiom(
                "identity", cls,
                {"property": key, "conflicts_with_existing": already},
                "low" if already else "high",
                f"`{key}` is unique and not-null across {table.rows:,} rows",
                ("This class ALREADY has a curated identity. The scanned column is the "
                 "raw source name; the curated one is the modelled warehouse name. "
                 "Accepting this replaces a deliberate decision with a source detail — "
                 "usually wrong. Set `override: true` only if you mean it."
                 if already else
                 "Without an identity no join condition can be derived, so every BI and "
                 "MDL projection of this class would be a guess.")))

        for col in table.columns:
            role, conf, ev, why = _role_for(col, key)
            axioms.append(Axiom(
                "property", f"{cls}.{col.name}",
                {"datatype": col.datatype, "role": role,
                 "required": col.not_null, "distinct": col.distinct},
                conf, ev, why))

    # -- relations, from foreign keys that resolve to a known identity --------
    for table in tables:
        cls = _class_name(table.name)
        for col in table.columns:
            if not (col.name.endswith("_id") and col.name != _identity_of(table)):
                continue
            stem = col.name[:-3]
            target = next((c for c in identities
                           if c.lower() == _class_name(stem).lower()), None)
            if target is None or target == cls:
                continue
            # Cardinality from the data, not the name: a foreign key whose values
            # are unique is a one-to-one, and calling it many-to-one silently
            # permits a fan-out that cannot happen.
            one_to_one = col.unique
            axioms.append(Axiom(
                "relation", f"{cls.lower()}_refers_to_{target.lower()}",
                {"domain": cls, "range": target,
                 "cardinality": "ONE_TO_ONE" if one_to_one else "MANY_TO_ONE",
                 "via": col.name,
                 "label": f"refers to {target.lower()}",
                 "inverse": f"has {cls.lower()}"},
                "high" if not one_to_one else "medium",
                f"`{col.name}` has {col.distinct} distinct values over {col.rows:,} rows",
                "Foreign key resolves to a scanned entity. Rename the relation to the "
                "business verb — `places`, `settles`, `holds` — before approving; "
                "`refers_to` is a placeholder, not a meaning."))

    return axioms
