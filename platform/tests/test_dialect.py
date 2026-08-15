"""Tests for SQL portability detection and the cross-database macro toolkits.

The bug class this exists to prevent is a build that passes while being wrong, so
most of what is pinned here is the *refusal* to translate rather than the
translation. Nothing in this module edits SQL. It says which call sites need
wrapping and in which macro; a human wraps them.

The macros themselves are tested where it counts — compiled through dbt against a
real adapter in `test_toolkit_macros.py`. What is checked here is that the
registry and the toolkit agree, because a remedy naming a macro nobody wrote
wastes more time than no remedy at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pf.onboard.dialect import (
    AMBIGUOUS,
    TOOLKITS,
    UNSUPPORTED,
    analyse,
    call_sites,
    resolvable,
    toolkit_macros,
)

ROOT = Path(__file__).resolve().parents[2]


# ------------------------------------------------------------- registries ----
def test_ambiguous_functions_are_never_auto_translated() -> None:
    """The whole design rests on this line. `date_trunc` exists in DuckDB and in
    BigQuery with the arguments reversed, so translating it silently would
    produce a warehouse that runs and lies."""
    assert not (set(UNSUPPORTED) & set(AMBIGUOUS))


def test_every_registered_replacement_macro_exists() -> None:
    """A remedy pointing at a macro nobody wrote is worse than no remedy."""
    available = toolkit_macros(ROOT)
    assert available, "no toolkit macros found — is the path right?"
    missing = {name: r.macro for name, r in UNSUPPORTED.items()
               if r.macro not in available}
    assert not missing, f"registry names macros that do not exist: {missing}"


def test_ambiguous_entries_say_what_to_do_about_it() -> None:
    for name, why in AMBIGUOUS.items():
        assert len(why) > 30, f"{name} needs a reason a human can act on"


def test_toolkit_macros_are_discovered_not_hardcoded() -> None:
    """Adding a `dbt-bigquery` sibling should need no change here."""
    for toolkit in TOOLKITS:
        assert (ROOT / "platform" / "toolkits" / toolkit / "macros").is_dir()
    assert {"sf_iff", "sf_datediff", "sf_least"} <= toolkit_macros(ROOT)


def test_adapter_variants_are_not_reported_as_public_macros() -> None:
    """`default__sf_iff` is dispatch plumbing, not something to call."""
    macros = toolkit_macros(ROOT)
    assert not any(m.startswith("default__") or "__" in m for m in macros)


# ------------------------------------------------------------- resolution ----
def test_catalogue_gaps_do_not_read_as_missing() -> None:
    """`duckdb_functions()` omits `coalesce` and `percentile_cont` while both
    work. Trusting the catalogue alone reports portability problems that do not
    exist, which is how a tool teaches people to ignore it."""
    assert {"coalesce", "percentile_cont", "grouping"} <= resolvable(
        {"coalesce", "percentile_cont", "grouping"})


def test_a_genuinely_missing_function_is_still_missing() -> None:
    assert "totally_made_up_fn" not in resolvable({"totally_made_up_fn"})
    assert "iff" not in resolvable({"iff"})


def test_type_names_in_casts_are_not_function_calls(tmp_path: Path) -> None:
    """`numeric(18, 2)` matches any regex looking for `name(`."""
    f = tmp_path / "m.sql"
    f.write_text("select cast(x as numeric(18,2)), cast(y as varchar(50)) from t")
    assert "numeric" not in call_sites([f])


# --------------------------------------------------------------- scanning ----
def test_substring_matches_do_not_invent_call_sites(tmp_path: Path) -> None:
    """`datediff(` ends in `iff(`. A substring scan reports 182 uses of a
    function the project never calls, and someone then builds a macro for it."""
    f = tmp_path / "m.sql"
    f.write_text("select datediff('day', a, b) from t")
    calls = call_sites([f])
    assert calls["datediff"] == 1
    assert "iff" not in calls


def test_already_portable_calls_are_not_reported(tmp_path: Path) -> None:
    """`{{ dbt.dateadd(...) }}` and an already wrapped `{{ sf_iff(...) }}` are
    portable. Counting them sends someone to fix what is finished."""
    f = tmp_path / "m.sql"
    f.write_text(
        "-- iff(a,b,c) in a comment\n"
        "{{ dbt.dateadd('day', 1, 'x') }}\n"
        "{{ sf_iff('a', 1, 0) }}\n"
        "select fake_fn(1), 'iff(' as literal from t\n")
    assert call_sites([f]) == {"fake_fn": 1}


def test_analyse_separates_the_three_outcomes(tmp_path: Path) -> None:
    f = tmp_path / "m.sql"
    f.write_text("select iff(a, 1, 0), date_trunc('month', d), no_such_fn(x) from t")
    r = analyse([f])
    assert r.covered == {"iff": 1}, "unresolvable, and a macro exists"
    assert r.ambiguous == {"date_trunc": 1}, "resolvable, and means something else"
    assert r.unsupported == {"no_such_fn": 1}, "unresolvable, no macro"
    assert r.blocking


def test_the_report_names_the_macro_to_use(tmp_path: Path) -> None:
    f = tmp_path / "m.sql"
    f.write_text("select iff(a, 1, 0) from t")
    assert analyse([f]).macro_for("iff") == "sf_iff"


def test_a_projects_own_macros_resolve(tmp_path: Path) -> None:
    f = tmp_path / "m.sql"
    f.write_text("select my_local_helper(a, b) from t")
    assert analyse([f], local_macros={"my_local_helper"}).clean


@pytest.mark.parametrize("name", ["least", "greatest"])
def test_null_semantics_split_is_flagged_not_translated(name: str) -> None:
    """These resolve everywhere and disagree only on sparse rows, so the
    difference reaches a dashboard before it reaches a test."""
    assert name in AMBIGUOUS
    assert "NULL" in AMBIGUOUS[name]


def test_star_expression_syntax_is_not_a_call_site(tmp_path: Path) -> None:
    """`select * exclude (col)` is DuckDB and Snowflake star syntax, not a
    function. No catalogue lists it as one, and `pf gen-staging` emits `exclude`
    in every staging model it writes — so without these words the scanner
    reported this platform's own generated SQL as unportable."""
    f = tmp_path / "stg_x.sql"
    f.write_text("select * exclude (_dlt_load_id) rename (a as b) "
                 "from {{ ref('r') }}")
    assert not (set(call_sites([f])) & {"exclude", "rename"})


def test_generated_staging_sql_scans_clean(tmp_path: Path) -> None:
    f = tmp_path / "stg_x.sql"
    f.write_text("select * exclude (_dlt_load_id) rename (a as b) from {{ ref('r') }}")
    assert analyse([f], local_macros=set()).clean
