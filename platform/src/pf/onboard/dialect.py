"""Which SQL functions a repository calls, and whether they will survive a move.

This module deliberately does not know what Snowflake is. Hardcoding one vendor's
function list means the next import from BigQuery or Redshift gets no warning at
all, so the question asked here is the general one: *this SQL calls these
functions — can the target warehouse answer them, and will it answer the same
way?* The first half comes from DuckDB at runtime, so it stays correct as DuckDB
gains built-ins instead of drifting against a list someone has to remember.

The answer to both halves is the `dbt-snowflake` toolkit, whose `sf_*` macros
compile to whatever the target adapter understands. That makes this a *reporting*
module rather than a translating one: it says which call sites need wrapping and
which macro to wrap them in, and a human does the wrapping. Nothing here edits
SQL, because the two failure classes below need different amounts of thought and
only one of them announces itself.

``UNSUPPORTED``  DuckDB cannot resolve the name. The build fails immediately,
                 someone reads the error, and it gets fixed. Loud and cheap.
``AMBIGUOUS``    DuckDB resolves the name and means something else by it.
                 `date_trunc` exists in DuckDB *and* in BigQuery with the
                 arguments reversed; `least` skips NULLs where Snowflake
                 propagates them. The build passes, the numbers are wrong, and
                 nothing says so. This is the class worth the noise.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

#: Where the portable macros live. One toolkit per source dialect; a `dbt-bigquery`
#: sibling would be added here and in a project's `macro-paths`.
TOOLKITS = ("dbt-snowflake",)

# Comments, string literals and Jinja, stripped before scanning. A function name
# inside a comment or a `{{ ref() }}` is not a call site.
_JINJA = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}", re.DOTALL)
_COMMENT = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)
_STRING = re.compile(r"'(?:[^']|'')*'")
_CALL = re.compile(r"\b([a-z_][a-z0-9_]*)\s*\(", re.IGNORECASE)

#: Reserved words that take a parenthesis and are not function calls.
#: Kept as prose rather than a list literal: these are word lists that get read
#: and amended, and a flat literal of eighty quoted strings is materially harder
#: to scan for a missing entry.
#:
#: The last line is star-expression syntax — `select * exclude (col)`,
#: `* rename (a as b)`, `columns(*)`. DuckDB and Snowflake both spell it this
#: way, no catalogue lists it as a function, and `pf gen-staging` emits
#: `exclude` in every staging model it writes: without these words the scanner
#: reported this platform's own generated SQL as unportable.
_KEYWORDS = frozenset("""
and as between by case cast distinct else end exists filter from full group
having if in inner interval into is join lateral left like limit map not null
offset on or order outer over partition pivot qualify returning right row
select struct then union unnest unpivot using values when where window with
within array all any some grouping rollup cube tablesample asof anti semi
positional describe summarize prepare execute attach detach copy insert update
delete create drop alter set sets reset call export import pragma recursive
exclude rename columns
""".split())  # noqa: SIM905

#: Forms DuckDB parses as syntax rather than registering as functions, so their
#: absence from `duckdb_functions()` is not evidence of anything. `coalesce` and
#: `grouping` really are missing from the catalogue while working perfectly.
_SYNTAX = frozenset({"cast", "try_cast", "extract", "substring", "trim",
                     "position", "overlay", "collate", "exists", "coalesce",
                     "grouping", "ifnull", "nullif"})

#: Ordered-set aggregates, only callable with `WITHIN GROUP` and so reported as
#: missing by both the catalogue and a bare probe.
_ORDERED_SET = frozenset({"percentile_cont", "percentile_disc", "mode"})

#: Type names, which appear as `numeric(18,2)` inside a cast and are matched by
#: any regex looking for `name(`. Not functions, and never missing.
_TYPES = frozenset("""
numeric decimal varchar char character int integer bigint smallint tinyint
float double real boolean bool date time timestamp timestamptz timestamp_ntz
timestamp_tz datetime interval blob bytea uuid json jsonb struct list array map
hugeint ubigint uinteger usmallint utinyint bit enum text string number binary
varbinary nvarchar nchar money geography geometry variant object
""".split())  # noqa: SIM905


@dataclass(frozen=True)
class Replacement:
    """A raw function call, and the portable macro that replaces it."""

    macro: str
    #: Which dialects spell it this way. Reported, never used to decide anything.
    seen_in: str
    note: str = ""


#: Names DuckDB cannot resolve. The build fails until these are wrapped.
UNSUPPORTED: dict[str, Replacement] = {
    "iff": Replacement("sf_iff", "Snowflake, SQL Server"),
    "nvl": Replacement("sf_nvl", "Oracle, Redshift, Snowflake"),
    "nvl2": Replacement("sf_nvl2", "Oracle, Redshift"),
    "zeroifnull": Replacement("sf_zeroifnull", "Snowflake, Teradata"),
    "nullifzero": Replacement("sf_nullifzero", "Snowflake, Teradata"),
    "div0": Replacement("sf_div0", "Snowflake",
                        "Snowflake's div0 returns 0 on a zero divisor, not NULL"),
    "div0null": Replacement("sf_div0null", "Snowflake"),
    "safe_divide": Replacement("sf_safe_divide", "BigQuery",
                               "returns NULL, unlike div0"),
    "getdate": Replacement("sf_getdate", "Redshift, SQL Server"),
    "sysdate": Replacement("sf_sysdate", "Oracle, Snowflake"),
    "charindex": Replacement("sf_charindex", "Snowflake, SQL Server",
                             "DuckDB's instr takes the arguments the other way round"),
    "regexp_substr": Replacement("sf_regexp_substr", "Snowflake, Oracle"),
    "regexp_like": Replacement("sf_regexp_like", "Snowflake, Oracle"),
    "to_varchar": Replacement("sf_to_varchar", "Snowflake"),
    "to_number": Replacement("sf_to_number", "Snowflake"),
    "try_to_number": Replacement("sf_try_to_number", "Snowflake"),
    "dayofweek": Replacement("sf_dayofweek", "Snowflake, MySQL",
                             "week numbering differs by warehouse"),
    "dateadd": Replacement("sf_dateadd", "Snowflake, Redshift, SQL Server"),
}

#: Names DuckDB *can* resolve and means something else by. The dangerous set.
#: The value is why a human has to look, not a translation.
AMBIGUOUS: dict[str, str] = {
    "date_trunc": ("DuckDB and Snowflake take (part, date); BigQuery takes "
                   "(date, part). Reversed arguments parse cleanly and return "
                   "wrong dates. Use {{ sf_date_trunc(part, col) }}."),
    "datediff": ("Snowflake takes (part, start, end); dbt's own macro takes "
                 "(start, end, part), and Redshift accepts an unquoted part "
                 "DuckDB will not. Use {{ sf_datediff(part, start, end) }}."),
    "date_diff": ("BigQuery takes (end, start, part) — the reverse of DuckDB. "
                  "Sign-flipped results in the wrong unit. Use "
                  "{{ sf_datediff(part, start, end) }}."),
    "datetime_diff": "BigQuery argument order — (end, start, part).",
    "timestamp_diff": "BigQuery argument order — (end, start, part).",
    "date_add": ("BigQuery takes (date, INTERVAL n part); DuckDB takes "
                 "(part, interval). Use {{ sf_dateadd(part, n, col) }}."),
    "last_day": ("Snowflake accepts a second part argument DuckDB does not. "
                 "Use {{ sf_last_day(col, part) }}."),
    "least": ("Snowflake returns NULL if any argument is NULL; DuckDB, Postgres "
              "and BigQuery skip NULLs. Silent, and only shows on sparse rows. "
              "Use {{ sf_least([...]) }} for Snowflake's rule."),
    "greatest": ("Snowflake returns NULL if any argument is NULL; DuckDB, "
                 "Postgres and BigQuery skip NULLs. Use {{ sf_greatest([...]) }}."),
    "to_date": ("Format models differ between Snowflake, Oracle and BigQuery. "
                "The no-format form is safe; a format string is not."),
    "to_char": "Format models differ by dialect.",
    "listagg": ("Supported, but WITHIN GROUP ordering syntax differs and "
                "unordered aggregation is non-deterministic. Use "
                "{{ sf_listagg(col, delim, order_by) }}."),
    "split_part": ("Negative part numbers are supported inconsistently. Use "
                   "{{ sf_split_part(col, delim, n) }}."),
}


@dataclass
class Report:
    """What a repository's SQL asks for, against what the target provides."""

    #: function -> call sites, for everything the scan found
    calls: Counter = field(default_factory=Counter)
    #: unresolvable, and a toolkit macro exists — wrap these or the build fails
    covered: Counter = field(default_factory=Counter)
    #: unresolvable with no macro — port by hand
    unsupported: Counter = field(default_factory=Counter)
    #: resolvable but dialect-dependent — wrap these or the numbers lie
    ambiguous: Counter = field(default_factory=Counter)

    @property
    def blocking(self) -> bool:
        return bool(self.covered or self.unsupported or self.ambiguous)

    @property
    def clean(self) -> bool:
        return not self.blocking

    def macro_for(self, name: str) -> str:
        r = UNSUPPORTED.get(name)
        return r.macro if r else ""


def toolkit_macros(root: Path) -> set[str]:
    """Every macro the dialect toolkits actually define.

    Read from the toolkit rather than assumed, so the registry above cannot claim
    a replacement that does not exist — a remedy naming a macro nobody wrote
    wastes more time than no remedy at all.
    """
    found: set[str] = set()
    rx = re.compile(r"\{%-?\s*macro\s+(\w+)\s*\(")
    for toolkit in TOOLKITS:
        d = root / "platform" / "toolkits" / toolkit / "macros"
        for f in sorted(d.glob("*.sql")) if d.exists() else []:
            found |= {
                m for m in rx.findall(f.read_text())
                if not m.startswith(("default__", "_")) and "__" not in m
            }
    return found


def duckdb_functions() -> set[str]:
    """Every function name DuckDB registers in its catalogue.

    Queried rather than hardcoded so the answer improves when DuckDB does. On its
    own it is not sufficient — see `resolvable`.
    """
    import duckdb

    con = duckdb.connect()
    try:
        rows = con.sql("SELECT DISTINCT function_name FROM duckdb_functions()")
        return {r[0].lower() for r in rows.fetchall()}
    finally:
        con.close()


def resolvable(names: set[str]) -> set[str]:
    """Which of these names DuckDB can actually answer.

    Three sources, because no one of them is sufficient and trusting any one
    alone produces confident nonsense:

    1. `duckdb_functions()` — authoritative when a name is present, and
       incomplete when it is not. `coalesce` and `percentile_cont` both run
       perfectly and neither appears in it.
    2. The allowlists above, for parser-level forms and ordered-set aggregates
       that no catalogue row and no bare call can reveal.
    3. A binder probe for whatever is left. `SELECT f()` separates "no such
       function" from "wrong arguments", and only the first means missing.

    The probe is what makes this hold up as DuckDB changes: a name that becomes
    native stops being reported without anyone editing a list.
    """
    known = duckdb_functions() | _SYNTAX | _ORDERED_SET | _TYPES
    unknown = {n for n in names if n not in known}
    if not unknown:
        return names & known

    import duckdb

    con = duckdb.connect()
    try:
        for name in sorted(unknown):
            try:
                con.sql(f"SELECT {name}()").fetchall()
                known.add(name)
            except Exception as exc:  # noqa: BLE001 - the message is the signal
                if "does not exist" not in str(exc):
                    known.add(name)
    finally:
        con.close()
    return names & known


def call_sites(paths: list[Path]) -> Counter:
    """Count raw SQL function calls across files.

    Lexical, not a parse: dbt SQL is Jinja-templated and therefore not valid SQL
    until compiled, so there is nothing to hand a parser at this stage. Jinja is
    stripped first, which also means `{{ dbt.dateadd(...) }}` and an already
    wrapped `{{ sf_iff(...) }}` are correctly *not* counted — they are portable
    already, and reporting them would send someone to fix what is finished.
    """
    found: Counter = Counter()
    for path in paths:
        text = path.read_text(errors="ignore")
        for rx in (_COMMENT, _JINJA, _STRING):
            text = rx.sub(" ", text)
        for name in _CALL.findall(text):
            lowered = name.lower()
            if lowered in _KEYWORDS or lowered in _TYPES or len(lowered) < 2:
                continue
            found[lowered] += 1
    return found


def analyse(paths: list[Path], local_macros: set[str] | None = None) -> Report:
    """Resolve every call site against DuckDB, the project's macros and dbt."""
    local = {m.lower() for m in (local_macros or set())}

    r = Report(calls=call_sites(paths))
    native = resolvable(set(r.calls) - set(AMBIGUOUS))

    for name, n in r.calls.items():
        # Checked before support, because these are the ones DuckDB *does* have
        # and would otherwise pass silently — which is the whole problem.
        if name in AMBIGUOUS:
            r.ambiguous[name] = n
        elif name in native or name in local:
            continue
        elif name in UNSUPPORTED:
            r.covered[name] = n
        else:
            r.unsupported[name] = n
    return r
