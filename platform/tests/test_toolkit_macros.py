"""The dbt-snowflake toolkit, compiled through dbt against a real adapter.

Everything here runs dbt for real. Rendering the macros in a bare Jinja
environment would test the string templating and miss the part that matters:
`adapter.dispatch` picking a per-adapter implementation, and dbt-core's own
cross-database macros being handed their arguments in the right order.

The values asserted below are Snowflake's, not DuckDB's, and the two disagree in
three places on purpose:

* ``sf_least(1, NULL)`` is NULL. DuckDB would return 1.
* ``sf_div0(1, 0)`` is 0. A hand-written `a / nullif(b, 0)` returns NULL.
* ``sf_datediff('day', a, b)`` takes the part first. dbt's own macro takes it
  last, so passing Snowflake's arguments straight through gives a sign-flipped
  answer in the wrong unit.

Those three are the whole reason the toolkit exists rather than a find-and-replace.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLKIT = ROOT / "platform" / "toolkits" / "dbt-snowflake" / "macros"

PROBE = """
with t as (
    select 1 as a, 5 as b, DATE '2024-03-15' as d,
           cast(null as int) as n, 'abc' as s
)
select
    {{ sf_iff('b > 0', "'y'", "'n'") }}                as iff_v,
    {{ sf_nvl('n', '0') }}                             as nvl_v,
    {{ sf_nvl2('n', "'has'", "'none'") }}              as nvl2_v,
    {{ sf_ifnull('n', '9') }}                          as ifnull_v,
    {{ sf_zeroifnull('n') }}                           as zin_v,
    {{ sf_nullifzero('0') }}                           as niz_v,
    {{ sf_div0('a', '0') }}                            as div0_v,
    {{ sf_div0null('a', 'n') }}                        as div0null_v,
    {{ sf_safe_divide('a', '0') }}                     as safediv_v,
    {{ sf_least(['a', 'b']) }}                         as least_v,
    {{ sf_least(['a', 'n']) }}                         as least_null_v,
    {{ sf_greatest(['a', 'n']) }}                      as greatest_null_v,
    {{ sf_least_ignore_nulls(['a', 'n']) }}            as least_ignore_v,
    {{ sf_greatest_ignore_nulls(['a', 'n']) }}         as greatest_ignore_v,
    {{ sf_to_number('a') }}                            as tonumber_v,
    {{ sf_try_to_number("'not a number'") }}           as trynumber_v,
    {{ sf_to_date("'2024-03-15'") }}                   as todate_v,
    {{ sf_dayofweek('d') }}                            as dow_v,
    {{ sf_getdate() }}                                 as getdate_v,
    {{ sf_sysdate() }}                                 as sysdate_v,
    (select {{ sf_listagg('s', "'|'") }} from t)       as listagg_v,
    {{ sf_dateadd('month', 1, 'd') }}                  as dateadd_v,
    {{ sf_datediff('day', "DATE '2024-01-01'", 'd') }} as datediff_v,
    {{ sf_date_trunc('month', 'd') }}                  as trunc_v,
    {{ sf_last_day('d') }}                             as lastday_v,
    {{ sf_charindex("'b'", 's') }}                     as charindex_v,
    {{ sf_regexp_substr("'a123b'", "'[0-9]+'") }}      as regexp_v,
    {{ sf_regexp_like('s', "'^a'") }}                  as regexlike_v,
    {{ sf_to_varchar('a') }}                           as tovarchar_v,
    {{ sf_split_part("'x-y-z'", "'-'", 2) }}           as splitpart_v
from t
"""

#: Snowflake's answers. Where DuckDB's native behaviour differs, the comment says
#: what it would have returned instead.
EXPECTED = {
    "iff_v": "y",
    "nvl_v": 0,
    "nvl2_v": "none",
    "ifnull_v": 9,
    "zin_v": 0,
    "niz_v": None,
    "div0_v": 0,            # a plain nullif guard would give NULL
    "div0null_v": 0,        # NULL divisor treated as zero, then guarded
    "safediv_v": None,      # BigQuery's spelling really does return NULL
    "least_v": 1,
    "least_null_v": None,   # DuckDB natively returns 1
    "greatest_null_v": None,  # DuckDB natively returns 1
    "least_ignore_v": 1,    # the explicitly NULL-skipping variant
    "greatest_ignore_v": 1,
    "tonumber_v": 1,
    "trynumber_v": None,    # returns NULL rather than raising
    "dow_v": 5,             # 2024-03-15 is a Friday; Snowflake counts Sunday=0
    "datediff_v": 74,       # part-first; reversed args would not give this
    "charindex_v": 2,
    "regexp_v": "123",
    "regexlike_v": True,
    "tovarchar_v": "1",
    "splitpart_v": "y",
    "listagg_v": "abc",
}

DBT_PROJECT = """
name: 'probe'
version: '1.0.0'
config-version: 2
profile: 'probe'
model-paths: ["models"]
macro-paths: ["{toolkit}"]
target-path: "target"
"""

PROFILES = """
probe:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: "{db}"
      threads: 1
"""


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> dict:
    """Run the probe model through dbt once, and return its row."""
    if shutil.which("dbt") is None:
        pytest.skip("dbt not on PATH")

    d = tmp_path_factory.mktemp("probe")
    (d / "models").mkdir()
    (d / "models" / "probe.sql").write_text(PROBE, encoding="utf-8")
    (d / "dbt_project.yml").write_text(DBT_PROJECT.format(toolkit=TOOLKIT), encoding="utf-8")
    db = d / "probe.duckdb"
    (d / "profiles.yml").write_text(PROFILES.format(db=db), encoding="utf-8")

    proc = subprocess.run(
        ["dbt", "run", "--project-dir", str(d), "--profiles-dir", str(d)],
        capture_output=True, text=True, check=False)
    assert proc.returncode == 0, f"dbt run failed:\n{proc.stdout[-3000:]}"

    import duckdb

    con = duckdb.connect(str(db), read_only=True)
    try:
        result = con.sql("select * from probe")
        return dict(zip([c[0] for c in result.description], result.fetchone(), strict=False))
    finally:
        con.close()


@pytest.mark.parametrize("column", sorted(EXPECTED))
def test_macro_returns_the_source_dialects_answer(built: dict, column: str) -> None:
    assert built[column] == EXPECTED[column]


def test_dates_are_computed_not_merely_compiled(built: dict) -> None:
    assert str(built["dateadd_v"])[:10] == "2024-04-15"
    assert str(built["trunc_v"])[:10] == "2024-03-01"
    assert str(built["lastday_v"])[:10] == "2024-03-31"
    assert str(built["todate_v"])[:10] == "2024-03-15"


def test_clock_functions_resolve(built: dict) -> None:
    """Non-deterministic, so only their existence is worth asserting."""
    assert built["getdate_v"] is not None
    assert built["sysdate_v"] is not None


def test_null_propagation_differs_from_the_native_function(built: dict) -> None:
    """The pair that justifies the toolkit: same inputs, two defensible answers,
    and only one of them is what the source warehouse meant."""
    assert built["least_null_v"] is None, "Snowflake propagates NULL"
    assert built["least_ignore_v"] == 1, "the _ignore_nulls variant does not"


def test_every_public_macro_is_exercised() -> None:
    """A macro nobody probes is a macro nobody has run."""
    from pf.onboard.dialect import toolkit_macros

    unprobed = {m for m in toolkit_macros(ROOT) if m not in PROBE}
    assert not unprobed, f"macros with no probe: {sorted(unprobed)}"
