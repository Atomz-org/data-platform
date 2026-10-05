"""Strict data contracts for what an agent may hand the platform.

Pydantic v2, `strict=True`, `frozen=True`, `extra="forbid"`. Strict means a
number arrives as a number and a string as a string — no coercion, because
coercion is where a model's malformed output becomes a well-formed record with
the wrong meaning. Frozen means a validated contract cannot be edited on the way
to disk. Forbidden extras mean a field the schema does not know is a rejection,
not a silent drop: an agent that invents `override_gate: true` should be told so.

The mart-name pattern is not a constant. Marts are named differently in every
entity and the platform is not allowed to know how, so the floor accepts any
snake_case identifier and each entity tightens it in `governance/aidf.yaml`.
The pattern reaches the validator through Pydantic's validation context:

    MartMetricContract.model_validate(payload, context={"mart_pattern": pattern})

which is how one class serves a thousand marts under a dozen conventions.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

#: Snake_case, 2-64 characters, no leading digit.
IDENT = r"^[a-z][a-z0-9_]{1,63}$"
#: An agent identifier: the loop name, the harness, or a person's handle.
AGENT = r"^[a-zA-Z0-9_\-.]{1,64}$"
#: The floor mart pattern, used when no context is supplied.
DEFAULT_MART_PATTERN = r"^[a-z][a-z0-9_]{1,127}$"

STRICT = ConfigDict(strict=True, frozen=True, extra="forbid", str_strip_whitespace=True)


class GovernanceStatus(StrEnum):
    """The execution status classification every governed action ends in.

    Mirrors the ledger: PASS is an `ok` execution after an `allow` decision;
    REJECT and CIRCUIT_BROKEN are `blocked` executions after a `deny`;
    ESCALATED is a `blocked` execution after a `hold` — the action waits for a
    person. `pf provenance verify` checks exactly this pairing.
    """

    PASS = "PASS"
    REJECT = "REJECT"
    CIRCUIT_BROKEN = "CIRCUIT_BROKEN"
    ESCALATED = "ESCALATED"


class AggregationType(StrEnum):
    SUM = "SUM"
    COUNT = "COUNT"
    COUNT_DISTINCT = "COUNT_DISTINCT"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"
    MEDIAN = "MEDIAN"
    PERCENTILE = "PERCENTILE"
    RATIO = "RATIO"
    DERIVED = "DERIVED"


class MetricStatus(StrEnum):
    VERIFIED = "verified"
    PROVISIONAL = "provisional"
    QUARANTINED = "quarantined"


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


class MartMetricContract(BaseModel):
    """One metric an agent proposes over one mart.

    `sql_definition` is a read-only projection — a SELECT, or an aggregation
    expression the platform wraps in one. The AST validator enforces that; this
    class only makes sure the field is there and bounded. `dependent_columns` is
    the agent's own claim of what it read, checked against what the SQL actually
    references and against the entity's catalogue.
    """

    model_config = STRICT

    mart_name: str = Field(description="Target mart, as dbt names the model.", min_length=2, max_length=128)
    metric_name: str = Field(pattern=IDENT, description="Canonical snake_case metric name.")
    label: str = Field(default="", max_length=120, description="Human title; empty inherits the name.")
    aggregation_type: AggregationType = Field(description="The operator that fixes the calculation's semantics.")
    sql_definition: str = Field(min_length=5, max_length=4096,
                                description="A pure SELECT projection or aggregation clause. No DDL, no DML.")
    dependent_columns: list[str] = Field(min_length=1, max_length=64,
                                         description="Source columns the definition references.")
    filter_expression: str = Field(default="", max_length=1024, description="Optional WHERE-style predicate.")
    rationale: str = Field(default="", max_length=2000, description="Why this metric, what question it answers.")
    author_agent: str = Field(pattern=AGENT, description="The loop, harness or person that produced it.")
    status: MetricStatus = Field(default=MetricStatus.PROVISIONAL)
    created_at_utc: datetime = Field(default_factory=_now)

    @field_validator("mart_name")
    @classmethod
    def _mart_matches_entity_pattern(cls, v: str, info: ValidationInfo) -> str:
        pattern = (info.context or {}).get("mart_pattern") or DEFAULT_MART_PATTERN
        if not re.match(pattern, v):
            raise ValueError(f"mart name {v!r} does not match this entity's pattern {pattern}")
        return v

    @field_validator("dependent_columns")
    @classmethod
    def _columns_are_identifiers(cls, v: list[str]) -> list[str]:
        bad = [c for c in v if not re.match(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$", c)]
        if bad:
            raise ValueError(f"not column identifiers: {bad}")
        if len({c.lower() for c in v}) != len(v):
            raise ValueError("dependent_columns repeats a column")
        return v

    @field_validator("created_at_utc")
    @classmethod
    def _timestamp_is_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None or v.utcoffset().total_seconds() != 0:
            raise ValueError("created_at_utc must be timezone-aware UTC")
        return v

    def canonical(self) -> dict[str, Any]:
        """A JSON-canonical dict: enums as values, the timestamp as RFC 3339 text.

        No floats anywhere, so the record can go straight into the provenance
        ledger, whose canonical form refuses them.
        """
        d = self.model_dump(mode="json")
        d["created_at_utc"] = self.created_at_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        return d


class SemanticMeasure(BaseModel):
    model_config = STRICT

    name: str = Field(pattern=IDENT)
    aggregation: AggregationType
    expression: str = Field(min_length=1, max_length=1024)
    description: str = Field(default="", max_length=1000)


class SemanticDimension(BaseModel):
    model_config = STRICT

    name: str = Field(pattern=IDENT)
    type: str = Field(pattern=r"^(categorical|time)$")
    expression: str = Field(default="", max_length=1024)
    time_granularity: str = Field(default="", pattern=r"^(|day|week|month|quarter|year)$")


class SemanticModelContract(BaseModel):
    """A semantic model an agent proposes over a mart: entities, dimensions and
    measures in MetricFlow's vocabulary, validated the same way a metric is."""

    model_config = STRICT

    name: str = Field(pattern=IDENT)
    mart_name: str = Field(min_length=2, max_length=128)
    description: str = Field(default="", max_length=2000)
    primary_entity: str = Field(pattern=IDENT)
    dimensions: list[SemanticDimension] = Field(default_factory=list, max_length=128)
    measures: list[SemanticMeasure] = Field(min_length=1, max_length=128)
    author_agent: str = Field(pattern=AGENT)
    created_at_utc: datetime = Field(default_factory=_now)

    @field_validator("mart_name")
    @classmethod
    def _mart_matches_entity_pattern(cls, v: str, info: ValidationInfo) -> str:
        pattern = (info.context or {}).get("mart_pattern") or DEFAULT_MART_PATTERN
        if not re.match(pattern, v):
            raise ValueError(f"mart name {v!r} does not match this entity's pattern {pattern}")
        return v

    def sql_fragments(self) -> list[str]:
        """Every expression the AST validator should look at."""
        return [m.expression for m in self.measures] + [d.expression for d in self.dimensions if d.expression]

    def canonical(self) -> dict[str, Any]:
        d = self.model_dump(mode="json")
        d["created_at_utc"] = self.created_at_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        return d


CONTRACTS: dict[str, type[BaseModel]] = {
    "mart_metric": MartMetricContract,
    "semantic_model": SemanticModelContract,
}


def json_schema(kind: str = "mart_metric") -> dict[str, Any]:
    """The schema an agent is shown before it answers. Same class, same rules."""
    return CONTRACTS[kind].model_json_schema()


def validate_payload(kind: str, payload: str | bytes | dict[str, Any], *, mart_pattern: str | None = None) -> BaseModel:
    """Validate an agent payload in strict *JSON* mode, whatever shape it arrives in.

    An agent's output is JSON, and strict JSON mode is the right strictness for
    it: a number must be a JSON number and a string a JSON string, an unknown
    field is refused — while an enum arrives as its value and a timestamp as
    RFC 3339 text, because that is the only way JSON can carry them. Strict
    *Python* mode would demand enum instances and datetime objects, which no
    model can emit. A dict is re-serialised so both paths judge the same bytes.
    """
    text = payload if isinstance(payload, (str, bytes)) else json.dumps(payload, default=str)
    context = {"mart_pattern": mart_pattern} if mart_pattern else None
    return CONTRACTS[kind].model_validate_json(text, context=context)
