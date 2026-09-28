"""Model-boundary validators: what an agent's output may contain.

Two validators, both pure Python, both usable without Guardrails installed:

  * `SqlAstValidator` parses the SQL with sqlglot and refuses anything that is
    not a read-only projection — DDL, DML, transaction control, system
    catalogues, file-reading table functions, `SELECT *` — and, given the
    entity's catalogue, any column or table the mart does not have. The last
    one is the hallucination check: a model that invents `customer_ltv` because
    the name sounds right is caught here, before the definition is written.

  * `PiiScrubber` refuses output carrying an e-mail address, an IP, a bearer
    token, a cloud key or a private key. It reports the *kind* and the position
    of a match and never the match itself, so a rejection record cannot become
    the leak it prevented.

They return a `Verdict` of `Finding`s rather than raising, because the engine
records every finding to the ledger whether or not the action goes ahead — a
rejection with no stated reason is a rejection nobody can appeal.

`pf.aidf.guardrails_adapter` wraps both as Guardrails validators
(`atomz/ast_sql_validator`, `atomz/pii_scrubber`) when that package is present.
The logic lives here so that the platform's gate does not depend on a package
whose dependency tree the workspace cannot carry.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError, TokenError

Severity = str  # "error" | "warn"


@dataclass(frozen=True)
class Finding:
    validator: str
    code: str
    message: str
    severity: Severity = "error"
    #: JSON path of the field the finding is about, when it is about one.
    path: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"validator": self.validator, "code": self.code, "message": self.message,
                "severity": self.severity, "path": self.path}


@dataclass
class Verdict:
    validator: str
    findings: list[Finding] = field(default_factory=list)
    #: What was actually examined — column counts, whether a catalogue was
    #: available. A pass with `catalog: absent` is a weaker pass and says so.
    checked: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not any(f.severity == "error" for f in self.findings)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    def to_dict(self) -> dict[str, Any]:
        return {"validator": self.validator, "ok": self.ok,
                "findings": [f.to_dict() for f in self.findings], "checked": self.checked}


# ------------------------------------------------------------------ SQL AST --
def _types(*names: str) -> tuple[type, ...]:
    """Expression classes by name, skipping any this sqlglot does not define.

    Named rather than imported so a sqlglot upgrade that adds `exp.Vacuum`
    costs one string here and one that renames a class degrades to a smaller
    forbidden set rather than an ImportError in the gate.
    """
    return tuple(t for t in (getattr(exp, n, None) for n in names) if isinstance(t, type))


#: Statements that change state. `DDL` and `DML` are sqlglot's own bases and
#: cover the common ones; the rest are named for the versions where they were
#: not yet under a base, and for the odd ones out (a `Command` is anything the
#: parser could not classify, which is exactly the thing not to execute).
FORBIDDEN_NODES: tuple[type, ...] = _types(
    "DDL", "DML", "Insert", "Update", "Delete", "Merge", "Drop", "Alter", "Create", "TruncateTable",
    "Command", "Set", "Copy", "Attach", "Detach", "Use", "Pragma", "Transaction", "Commit", "Rollback",
    "Grant", "Revoke", "Kill", "LoadData", "Cache", "Uncache", "Describe", "Show", "Analyze", "Vacuum",
    "Install", "Load", "Execute", "Call",
)

#: Table functions that read outside the warehouse, or leak the environment.
FORBIDDEN_FUNCTIONS: frozenset[str] = frozenset({
    "read_csv", "read_csv_auto", "read_parquet", "read_json", "read_json_auto", "read_json_objects",
    "read_text", "read_blob", "glob", "getenv", "current_setting", "load", "install", "duckdb_settings",
    "duckdb_secrets", "duckdb_extensions", "pg_read_file", "pg_ls_dir", "system", "http_get", "sqlite_scan",
    "postgres_scan", "mysql_scan", "iceberg_scan", "delta_scan",
})

DEFAULT_SYSTEM_SCHEMAS: frozenset[str] = frozenset({
    "information_schema", "pg_catalog", "sys", "system", "duckdb_internal", "mysql", "performance_schema",
})


class SqlAstValidator:
    """Read-only, explicit, catalogue-bound SQL — or a finding that says why not."""

    name = "sql_ast"

    def __init__(
        self,
        dialect: str = "duckdb",
        *,
        allowed_columns: Iterable[str] | None = None,
        allowed_tables: Iterable[str] | None = None,
        system_schemas: Iterable[str] | None = None,
        allow_star: bool = False,
        forbidden_functions: Iterable[str] | None = None,
    ) -> None:
        self.dialect = dialect or "duckdb"
        self.allowed_columns = {c.lower() for c in allowed_columns} if allowed_columns is not None else None
        self.allowed_tables = {t.lower() for t in allowed_tables} if allowed_tables is not None else None
        self.system_schemas = {s.lower() for s in (system_schemas or DEFAULT_SYSTEM_SCHEMAS)}
        self.allow_star = allow_star
        self.forbidden_functions = {f.lower() for f in (forbidden_functions or FORBIDDEN_FUNCTIONS)}

    # -- public -----------------------------------------------------------
    def validate(self, sql: str, *, path: str = "sql_definition") -> Verdict:
        v = Verdict(self.name, checked={
            "dialect": self.dialect,
            "catalog": "present" if self.allowed_columns is not None else "absent",
        })
        if not isinstance(sql, str) or not sql.strip():
            v.findings.append(Finding(self.name, "empty", "SQL payload must be a non-empty string", path=path))
            return v

        try:
            statements = [s for s in sqlglot.parse(sql, read=self.dialect) if s is not None]
        except (ParseError, TokenError) as exc:
            v.findings.append(Finding(self.name, "syntax", f"SQL does not parse as {self.dialect}: {str(exc)[:300]}",
                                      path=path))
            return v
        except Exception as exc:  # noqa: BLE001 — a parser crash is still a rejection, with the reason
            v.findings.append(Finding(self.name, "syntax", f"SQL parser failed: {type(exc).__name__}: {str(exc)[:300]}",
                                      path=path))
            return v

        if not statements:
            v.findings.append(Finding(self.name, "empty", "SQL parsed to nothing", path=path))
            return v
        if len(statements) > 1:
            v.findings.append(Finding(self.name, "multiple_statements",
                                      f"{len(statements)} statements; a definition is exactly one", path=path))
            return v

        stmt = statements[0]
        self._check_mutation(stmt, v, path)
        if not v.ok:
            return v  # nothing below is worth reporting on a statement that mutates
        self._check_shape(stmt, v, path)
        self._check_schemas_and_functions(stmt, v, path)
        self._check_catalog(stmt, v, path)
        return v

    def referenced_columns(self, sql: str) -> set[str]:
        """Column names the SQL reads, minus its own aliases. Empty on a parse error."""
        try:
            stmt = sqlglot.parse_one(sql, read=self.dialect)
        except Exception:  # noqa: BLE001
            return set()
        return self._columns(stmt)

    # -- checks -----------------------------------------------------------
    def _check_mutation(self, stmt: exp.Expression, v: Verdict, path: str) -> None:
        for node in stmt.walk():
            if isinstance(node, FORBIDDEN_NODES):
                v.findings.append(Finding(
                    self.name, "mutation",
                    f"{type(node).__name__} is not allowed: a metric definition is a read-only projection",
                    path=path))
                return

    def _check_shape(self, stmt: exp.Expression, v: Verdict, path: str) -> None:
        if self.allow_star:
            return
        selects = [stmt] if isinstance(stmt, exp.Select) else list(stmt.find_all(exp.Select))
        for sel in selects:
            for e in sel.expressions:
                if isinstance(e, exp.Star) or (isinstance(e, exp.Column) and isinstance(e.this, exp.Star)):
                    v.findings.append(Finding(
                        self.name, "star_projection",
                        "SELECT * is not an explicit projection; name the columns", path=path))
                    return

    def _check_schemas_and_functions(self, stmt: exp.Expression, v: Verdict, path: str) -> None:
        for t in stmt.find_all(exp.Table):
            for part in (t.db, t.catalog):
                if part and part.lower() in self.system_schemas:
                    v.findings.append(Finding(
                        self.name, "system_schema",
                        f"reads system catalogue `{part}`; metrics read the mart, not the engine", path=path))
                    break
            name = (t.name or "").lower()
            if name in self.forbidden_functions or name.startswith(("duckdb_", "pg_")):
                v.findings.append(Finding(self.name, "forbidden_function",
                                          f"`{t.name}` is not a mart", path=path))
        for fn in stmt.find_all(exp.Func):
            names = {n.lower() for n in fn.sql_names()} if hasattr(fn, "sql_names") else set()
            if isinstance(fn, exp.Anonymous):
                names.add(str(fn.this).lower())
            hit = names & self.forbidden_functions
            if hit:
                v.findings.append(Finding(self.name, "forbidden_function",
                                          f"`{sorted(hit)[0]}` reads outside the warehouse", path=path))

    def _ctes(self, stmt: exp.Expression) -> set[str]:
        return {c.alias_or_name.lower() for c in stmt.find_all(exp.CTE)}

    def _aliases(self, stmt: exp.Expression) -> set[str]:
        out = {a.alias.lower() for a in stmt.find_all(exp.Alias) if a.alias}
        for t in stmt.find_all(exp.Table):
            if t.alias:
                out.add(t.alias.lower())
        for sub in stmt.find_all(exp.Subquery):
            if sub.alias:
                out.add(sub.alias.lower())
        return out

    def _columns(self, stmt: exp.Expression) -> set[str]:
        aliases = self._aliases(stmt)
        cols: set[str] = set()
        for c in stmt.find_all(exp.Column):
            if isinstance(c.this, exp.Star):
                continue
            n = c.name.lower()
            if n and n not in aliases:
                cols.add(n)
        return cols

    def _check_catalog(self, stmt: exp.Expression, v: Verdict, path: str) -> None:
        cols = self._columns(stmt)
        v.checked["columns_referenced"] = sorted(cols)
        if self.allowed_columns is not None:
            unknown = sorted(cols - self.allowed_columns)
            v.checked["columns_checked"] = len(cols)
            if unknown:
                v.findings.append(Finding(
                    self.name, "hallucinated_column",
                    f"column(s) not in this mart's catalogue: {unknown}", path=path))
        if self.allowed_tables is not None:
            ctes = self._ctes(stmt)
            tables = {t.name.lower() for t in stmt.find_all(exp.Table) if t.name} - ctes
            unknown_t = sorted(tables - self.allowed_tables)
            v.checked["tables_referenced"] = sorted(tables)
            if unknown_t:
                v.findings.append(Finding(
                    self.name, "hallucinated_table",
                    f"table(s) not in this entity's catalogue: {unknown_t}", path=path))


# --------------------------------------------------------------------- PII --
#: Label -> pattern. Ordered from most to least specific so the first label a
#: value earns is the most useful one.
PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "PRIVATE_KEY": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "AWS_ACCESS_KEY": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "GITHUB_TOKEN": re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b"),
    "JWT": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    "GENERIC_SECRET": re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|password|passwd|pwd)\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-/+=.]{8,}['\"]?"),
    "BEARER": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9_\-.=]{16,}"),
    "EMAIL": re.compile(r"\b[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9-.]+\b"),
    "IPV4": re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"),
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}(?:\s?[A-Z0-9]{1,4})?\b"),
}

#: Values the IPV4 pattern matches that are not addresses of anything —
#: version strings, semantic versions in comments.
_IPV4_NOISE = re.compile(r"^(?:0\.0\.0\.0|127\.0\.0\.1|\d+\.\d+\.\d+\.\d+)$")


class PiiScrubber:
    """Refuse output carrying personal data or a credential. Never echo it."""

    name = "pii"

    def __init__(self, allow: Iterable[str] | None = None, patterns: dict[str, re.Pattern[str]] | None = None) -> None:
        self.allow = [re.compile(a) for a in (allow or [])]
        self.patterns = patterns or PII_PATTERNS

    def _allowed(self, text: str) -> bool:
        return any(a.search(text) for a in self.allow)

    def validate(self, value: str, *, path: str = "") -> Verdict:
        v = Verdict(self.name, checked={"chars": len(value) if isinstance(value, str) else 0})
        if not isinstance(value, str):
            v.findings.append(Finding(self.name, "type", "payload must be a string", path=path))
            return v
        for label, pat in self.patterns.items():
            for m in pat.finditer(value):
                hit = m.group(0)
                if self._allowed(hit):
                    continue
                if label == "IPV4" and hit in ("0.0.0.0", "127.0.0.1"):
                    continue
                v.findings.append(Finding(
                    self.name, label.lower(),
                    f"{label} detected at offset {m.start()} ({len(hit)} chars); redact it", path=path))
                break  # one finding per kind is enough to reject, and says nothing more
        return v

    def validate_payload(self, payload: Any, *, path: str = "$") -> Verdict:
        """Every string leaf of a JSON-like structure, with its path."""
        v = Verdict(self.name, checked={"fields": 0})
        for p, s in _string_leaves(payload, path):
            v.checked["fields"] += 1
            sub = self.validate(s, path=p)
            v.findings.extend(sub.findings)
        return v


def _string_leaves(obj: Any, path: str) -> Iterable[tuple[str, str]]:
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, val in obj.items():
            yield from _string_leaves(val, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, val in enumerate(obj):
            yield from _string_leaves(val, f"{path}[{i}]")


#: Registry by the names `runtime.validators` uses.
VALIDATORS = {"sql_ast": SqlAstValidator, "pii": PiiScrubber}
