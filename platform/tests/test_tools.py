"""Tests for the pluggable tool layer.

The properties worth pinning down are the ones a future tool could quietly
break: that a tool cannot loosen the gate, that discovery survives a broken
third party, that group enablement actually reaches a sister, and that listing
tools does not import their implementations.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from pf.capabilities import Capability
from pf.tools import config as tool_config
from pf.tools import registry
from pf.tools.spec import (
    DbtBinding, InvalidTool, Requirement, Surface, Tool, ToolContext,
)


# ------------------------------------------------------------ gate safety --
def test_tool_may_tighten_the_gate() -> None:
    t = Tool(
        name="tightener", title="T", summary="s",
        capability=Capability(name="tightener", description="d",
                              gate={"denylist": ["**/secret/**"],
                                    "impact_required": ["**/models/**"]}),
    )
    assert t.gate_sections()["denylist"] == ["**/secret/**"]


@pytest.mark.parametrize("section", ["denylist_except", "autoMergeAllowlist",
                                     "maxFiles", "blockOn"])
def test_tool_cannot_loosen_the_gate(section: str) -> None:
    """The whole reason capabilities were kept declarative. A tool that could add
    to `denylist_except` would be able to exempt itself from the policy."""
    with pytest.raises(InvalidTool, match="loosen"):
        Tool(name="loosener", title="T", summary="s",
             capability=Capability(name="loosener", description="d",
                                   gate={section: ["**/anything/**"]}))


def test_invalid_scope_is_rejected_at_construction() -> None:
    with pytest.raises(InvalidTool):
        Tool(name="x", title="X", summary="s", scope=frozenset({"universe"}))


def test_empty_scope_is_rejected() -> None:
    with pytest.raises(InvalidTool):
        Tool(name="x", title="X", summary="s", scope=frozenset())


# -------------------------------------------------------------- discovery --
def test_recce_is_registered_and_declares_both_scopes() -> None:
    tools = registry.all_tools()
    assert "recce" in tools
    t = tools["recce"]
    assert t.supports("group") and t.supports("project")
    assert t.dbt is not None and t.dbt.needs_baseline


def test_discovery_reports_a_broken_source_instead_of_raising(monkeypatch) -> None:
    """A third-party tool that explodes on import must not take down `pf`."""
    monkeypatch.setattr(registry, "BUILTIN_MODULES",
                        ("pf.tools.recce", "pf.tools.does_not_exist"))
    found, errors = registry.discover()
    assert "recce" in found                      # the good one still loads
    assert any("does_not_exist" in str(e) for e in errors)


def test_get_unknown_tool_raises() -> None:
    with pytest.raises(InvalidTool, match="unknown tool"):
        registry.get("no-such-tool")


def test_listing_does_not_import_the_tool_implementation() -> None:
    """Hooks are dotted strings precisely so this holds. If `pf tool list` had to
    import every tool, a tool whose dependencies are absent would break the
    command you need in order to find that out."""
    t = registry.all_tools()["recce"]
    assert isinstance(t.dagster, str) and ":" in t.dagster
    assert isinstance(t.bootstrap, str) and ":" in t.bootstrap


def test_requirements_report_missing_without_raising() -> None:
    r = Requirement("binary", "definitely-not-a-real-binary-xyz", "install it")
    assert r.satisfied() is False
    t = Tool(name="x", title="X", summary="s", requires=(r,))
    assert t.installed is False
    assert [m.describe() for m in t.missing()] == ["binary:definitely-not-a-real-binary-xyz"]


# ----------------------------------------------------------- inheritance --
def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body))


def test_group_enablement_reaches_a_sister(tmp_path: Path) -> None:
    _write(tmp_path / "groups" / "acme" / "tools.yaml", """\
        version: 1
        tools:
          recce:
            enabled: true
            config: {port: 8000}
        """)
    (tmp_path / "groups" / "acme" / "projects" / "acme-us").mkdir(parents=True)

    resolved = tool_config.resolve(tmp_path, "acme", "acme-us")
    assert resolved["recce"].enabled is True
    assert resolved["recce"].source == "group"
    assert resolved["recce"].config["port"] == 8000


def test_project_can_opt_out_of_a_group_decision(tmp_path: Path) -> None:
    _write(tmp_path / "groups" / "acme" / "tools.yaml", """\
        version: 1
        tools: {recce: {enabled: true}}
        """)
    _write(tmp_path / "groups" / "acme" / "projects" / "acme-eu" / "tools.yaml", """\
        version: 1
        tools: {recce: {enabled: false}}
        """)
    resolved = tool_config.resolve(tmp_path, "acme", "acme-eu")
    assert resolved["recce"].enabled is False
    assert resolved["recce"].source == "project"


def test_project_config_deep_merges_over_the_group(tmp_path: Path) -> None:
    """Overriding one key must not drop the rest, or a port change would silently
    reset every other setting the group made."""
    _write(tmp_path / "groups" / "acme" / "tools.yaml", """\
        version: 1
        tools:
          recce:
            enabled: true
            config: {port: 8000, strict: true}
        """)
    _write(tmp_path / "groups" / "acme" / "projects" / "acme-us" / "tools.yaml", """\
        version: 1
        tools:
          recce:
            config: {port: 8099}
        """)
    cfg = tool_config.resolve(tmp_path, "acme", "acme-us")["recce"]
    assert cfg.enabled is True          # inherited
    assert cfg.config == {"port": 8099, "strict": True}


def test_missing_config_files_are_not_an_error(tmp_path: Path) -> None:
    assert tool_config.resolve(tmp_path, "acme", "acme-us") == {}
    assert tool_config.enabled_names(tmp_path, "acme", "acme-us") == []


def test_write_round_trips(tmp_path: Path) -> None:
    tool_config.write(tmp_path, "acme", "", "recce", on=True, config={"port": 9})
    assert tool_config.resolve(tmp_path, "acme", "x")["recce"].enabled is True
    tool_config.write(tmp_path, "acme", "", "recce", on=False)
    assert tool_config.resolve(tmp_path, "acme", "x")["recce"].enabled is False


# ---------------------------------------------------------------- recce ----
def test_recce_config_falls_back_when_there_is_no_graph(tmp_path: Path) -> None:
    """A freshly scaffolded project has no models. Emitting checks against
    nothing would fail on first run."""
    from pf.tools.recce import generate_config

    cfg = generate_config(tmp_path)
    types = [c["type"] for c in cfg["checks"]]
    assert types == ["row_count_diff", "schema_diff"]


def test_recce_bootstrap_skips_a_project_without_dbt(tmp_path: Path) -> None:
    from pf.tools.recce import bootstrap_project

    r = bootstrap_project(tmp_path, "acme", "acme-us", tmp_path, {})
    assert r.status == "skipped"


def test_recce_config_is_idempotent(tmp_path: Path) -> None:
    from pf.tools.recce import write_config

    (tmp_path / "transform").mkdir()
    _, first = write_config(tmp_path)
    _, second = write_config(tmp_path)
    assert first is True and second is False


def test_recce_baseline_requires_a_manifest(tmp_path: Path) -> None:
    from pf.tools.recce import capture_baseline

    (tmp_path / "transform" / "target").mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="manifest"):
        capture_baseline(tmp_path, rebuild=False)


def test_baseline_is_a_build_not_a_copy(tmp_path: Path, monkeypatch) -> None:
    """The correctness of every value diff rests on this.

    Copying `target/` aside yields a base manifest whose nodes resolve to the
    same relations as the current one, so a diff compares each table with itself
    and reports clean on every change. The baseline has to be materialised into
    the `base` target instead.
    """
    from pf.tools import recce as recce_mod

    target = tmp_path / "transform" / "target"
    target.mkdir(parents=True)
    (target / "manifest.json").write_text("{}")

    calls: list[dict] = []

    class _Proc:
        returncode = 0
        stdout = stderr = ""

    def fake_dbt(project_dir, *args, **kwargs):
        calls.append({"args": args, "target": kwargs.get("target")})
        return _Proc()

    monkeypatch.setattr("pf.runtime.dbt_runtime.dbt", fake_dbt)
    recce_mod.capture_baseline(tmp_path)

    assert calls, "capture_baseline must build, not just copy artefacts"
    assert calls[0]["args"][0] == "build"
    assert all(c["target"] == "base" for c in calls), \
        "the baseline must materialise into the `base` target, not the live one"


def test_baseline_build_failure_is_fatal(tmp_path: Path, monkeypatch) -> None:
    """A half-built comparison environment produces diffs against missing tables,
    which read as deletions. Better to refuse than to report fiction."""
    from pf.tools import recce as recce_mod

    target = tmp_path / "transform" / "target"
    target.mkdir(parents=True)
    (target / "manifest.json").write_text("{}")

    class _Proc:
        returncode = 1
        stdout = "boom"
        stderr = ""

    monkeypatch.setattr("pf.runtime.dbt_runtime.dbt", lambda *a, **k: _Proc())
    with pytest.raises(RuntimeError, match="baseline build failed"):
        recce_mod.capture_baseline(tmp_path)


def test_keyless_mart_still_gets_money_coverage() -> None:
    """fct_revenue has no natural key. Requiring one left exactly the aggregate
    marts — where a changed metric filter hides — with no value-level check."""
    import pf.tools.recce as recce_mod

    # A keyless mart carrying a money column — fct_revenue's shape.
    original = recce_mod._reviewable_models
    recce_mod._reviewable_models = lambda _p: [
        _model(net_amount=("money_amount", "distribution", False))]
    try:
        cfg = recce_mod.generate_config(Path("/nonexistent"))
    finally:
        recce_mod._reviewable_models = original

    types = [c["type"] for c in cfg["checks"]]
    assert "profile_diff" in types, "a keyless mart must still have its amounts profiled"
    assert "value_diff" not in types, "a value diff without a key cannot align rows"


# ------------------------------------------------- ontology <-> review ----
def test_review_intent_is_inferred_from_datatype() -> None:
    """A role added to the ontology tomorrow must be reviewed without anyone
    remembering to wire it up here."""
    from pf.ontology.model import Role

    assert Role("discount_pct", datatype="decimal").review_intent == "distribution"
    assert Role("units", datatype="integer").review_intent == "distribution"
    # Whether a string is a bounded category or free text is not knowable from
    # the datatype, so it stays out of the review until declared.
    assert Role("some_label", datatype="string").review_intent == "none"


def test_explicit_review_intent_overrides_the_datatype_default() -> None:
    from pf.ontology.model import Role

    assert Role("plan_tier", datatype="string",
                review="categories").review_intent == "categories"


def test_pii_forces_none_even_when_review_is_declared() -> None:
    """The guard the `review-artifacts-exclude-pii` policy names. A value diff
    persists the compared rows into a durable, shared state file."""
    from pf.ontology.model import Role

    assert Role("pii_email", datatype="string", pii=True,
                review="categories").review_intent == "none"


def test_shipped_ontology_declares_intents_for_its_roles() -> None:
    from pf.ontology.model import load_ontology

    onto = load_ontology()
    assert onto.roles["natural_key"].review_intent == "identity"
    assert onto.roles["money_amount"].review_intent == "distribution"
    assert onto.roles["status_enum"].review_intent == "categories"
    for name in onto.pii_roles():
        assert onto.roles[name].review_intent == "none", f"{name} must not be diffed"


def _model(**cols: tuple[str, str, bool]):
    """Build a ReviewModel from {column: (role, intent, pii)}."""
    from pf.tools.recce import ReviewColumn, ReviewModel

    return ReviewModel(name="m", grain="one thing", columns=tuple(
        ReviewColumn(n, r, i, p) for n, (r, i, p) in cols.items()))


def test_value_diff_excludes_pii_columns(monkeypatch) -> None:
    import pf.tools.recce as recce_mod

    model = _model(id=("natural_key", "identity", False),
                   email=("pii_email", "none", True),
                   amount=("money_amount", "distribution", False))
    monkeypatch.setattr(recce_mod, "_reviewable_models", lambda _p: [model])
    checks = recce_mod.generate_config(Path("/nonexistent"))["checks"]

    vd = next(c for c in checks if c["type"] == "value_diff")
    assert "email" not in vd["params"]["columns"]
    assert set(vd["params"]["columns"]) == {"id", "amount"}
    # And no column-level check anywhere may name the PII column.
    for c in checks:
        params = c.get("params", {})
        assert "email" not in str(params.get("columns", "")), c["name"]
        assert params.get("column_name") != "email", c["name"]


def test_no_value_diff_when_the_only_key_is_pii(monkeypatch) -> None:
    """Keying on PII would materialise it as the join column of every diff row,
    which is the one column a value diff cannot omit."""
    import pf.tools.recce as recce_mod

    model = _model(email=("pii_email", "none", True),
                   amount=("money_amount", "distribution", False))
    monkeypatch.setattr(recce_mod, "_reviewable_models", lambda _p: [model])
    checks = recce_mod.generate_config(Path("/nonexistent"))["checks"]

    assert not [c for c in checks if c["type"] == "value_diff"]
    assert [c for c in checks if c["type"] == "profile_diff"]  # amounts still checked


def test_intents_map_to_recce_check_types(monkeypatch) -> None:
    import pf.tools.recce as recce_mod

    model = _model(id=("natural_key", "identity", False),
                   amount=("money_amount", "distribution", False),
                   status=("status_enum", "categories", False))
    monkeypatch.setattr(recce_mod, "_reviewable_models", lambda _p: [model])
    checks = recce_mod.generate_config(Path("/nonexistent"))["checks"]
    by_type = {c["type"] for c in checks}

    assert {"row_count_diff", "schema_diff", "value_diff",
            "profile_diff", "query_diff"} <= by_type


def test_category_drift_is_a_keyed_query_not_top_k(monkeypatch) -> None:
    """Regression: recce's top_k_diff returns parallel arrays and its differ uses
    `DeepDiff(ignore_order=True)`, so renaming a category moves a count between
    slots and both arrays stay equal as multisets. The check ran green while
    `starter` had become `basic`. A keyed group-by makes the same rename a row
    present on one side only."""
    import pf.tools.recce as recce_mod

    model = _model(status=("status_enum", "categories", False))
    monkeypatch.setattr(recce_mod, "_reviewable_models", lambda _p: [model])
    checks = recce_mod.generate_config(Path("/nonexistent"))["checks"]

    drift = next(c for c in checks if c["name"].startswith("Category drift"))
    assert drift["type"] == "query_diff"
    assert drift["params"]["primary_keys"] == ["category"]
    assert "group by" in drift["params"]["sql_template"]
    assert "ref('m')" in drift["params"]["sql_template"]
    assert not [c for c in checks if c["type"] == "top_k_diff"]


def test_ensure_base_target_is_idempotent(tmp_path: Path) -> None:
    from pf.tools.recce import ensure_base_target

    (tmp_path / "transform").mkdir()
    assert ensure_base_target(tmp_path, "demo") is True    # written
    assert ensure_base_target(tmp_path, "demo") is False   # already present


def test_recce_run_reports_missing_binary_rather_than_raising(tmp_path: Path, monkeypatch) -> None:
    """"revenue moved" and "recce is not installed" must never be the same signal."""
    from pf.tools import recce as recce_mod

    (tmp_path / "transform").mkdir()

    def boom(*a, **k):
        raise FileNotFoundError("recce")

    monkeypatch.setattr(recce_mod.subprocess, "run", boom)
    result = recce_mod.run(tmp_path)
    assert result["ok"] is False and result["reason"] == "not_installed"


def test_server_argv_uses_review_mode_only_with_state(tmp_path: Path) -> None:
    from pf.tools.recce import STATE_FILE, server_argv

    (tmp_path / "transform").mkdir()
    assert "--review" not in server_argv(tmp_path)
    (tmp_path / "transform" / STATE_FILE).write_text("{}")
    argv = server_argv(tmp_path)
    assert "--review" in argv
    # Positional, and last — `recce server --review <state>`. It was passed as
    # `--state-file <state>`, an option recce does not define, so the server
    # exited on startup every time.
    assert argv[-1] == STATE_FILE
    assert "--state-file" not in argv


# ------------------------------------------------------------- contracts --
def test_tool_context_renders_surface_argv(tmp_path: Path) -> None:
    ctx = ToolContext(root=tmp_path, group="acme", project="acme-us",
                      project_dir=tmp_path, dbt_dir=tmp_path / "transform",
                      config={"port": 8123})
    assert ctx.render(("recce", "server", "--port", "{port}"))[-1] == "8123"


def test_surface_url() -> None:
    assert Surface(port=8000).url() == "http://127.0.0.1:8000/"


def test_dbt_binding_defaults() -> None:
    b = DbtBinding()
    assert b.baseline_dir == "target-base" and b.needs_manifest is False


# ------------------------------------------------------- model attribution --
def _state(tmp_path: Path, payload: dict) -> Path:
    import json

    from pf.tools.recce import STATE_FILE

    (tmp_path / "transform").mkdir(exist_ok=True)
    (tmp_path / "transform" / STATE_FILE).write_text(json.dumps(payload))
    return tmp_path


def test_model_diffs_is_empty_without_a_review(tmp_path: Path) -> None:
    from pf.tools.recce import model_diffs

    assert model_diffs(tmp_path) == {}


def test_row_count_diff_attributes_itself_and_flags_movement(tmp_path: Path) -> None:
    from pf.tools.recce import model_diffs

    _state(tmp_path, {"checks": [{"check_id": "c1", "name": "Row count diff"}],
                      "runs": [{"type": "row_count_diff", "check_id": "c1",
                                "result": {"fct_a": {"base": 10, "curr": 12},
                                           "fct_b": {"base": 5, "curr": 5}}}]})
    d = model_diffs(tmp_path)
    assert d["fct_a"]["row_count"] == {"base": 10, "curr": 12, "delta": 2}
    assert d["fct_a"]["moved"] is True
    assert d["fct_b"]["moved"] is False


def test_a_check_name_attributes_a_run_that_names_no_model(tmp_path: Path) -> None:
    """query_diff carries SQL, not a node — the name is the only link back."""
    from pf.tools.recce import model_diffs

    _state(tmp_path, {
        "checks": [{"check_id": "c1", "name": "Category drift — dim_customers.plan_tier"}],
        "runs": [{"type": "query_diff", "check_id": "c1",
                  "result": {"diff": {"columns": [], "data": [["basic", 3, True, False]]}}}]})
    d = model_diffs(tmp_path)
    assert d["dim_customers"]["categories_drifted"] == ["plan_tier"]
    assert d["dim_customers"]["moved"] is True


def test_an_empty_category_diff_is_not_movement(tmp_path: Path) -> None:
    from pf.tools.recce import model_diffs

    _state(tmp_path, {
        "checks": [{"check_id": "c1", "name": "Category drift — dim_customers.plan_tier"}],
        "runs": [{"type": "query_diff", "check_id": "c1",
                  "result": {"diff": {"columns": [], "data": []}}}]})
    d = model_diffs(tmp_path)
    assert d["dim_customers"]["moved"] is False
    assert d["dim_customers"]["checks"] == 1


def test_unparseable_state_is_not_an_exception(tmp_path: Path) -> None:
    from pf.tools.recce import STATE_FILE, model_diffs

    (tmp_path / "transform").mkdir()
    (tmp_path / "transform" / STATE_FILE).write_text("{not json")
    assert model_diffs(tmp_path) == {}


# -------------------------------------------------------------- scaffold --
def test_a_new_group_enables_the_tools_that_declare_a_default() -> None:
    """Registering a tool has to be the only step — see `default_enabled`."""
    import yaml

    from pf.scaffold.generator import _default_tools_yaml
    from pf.tools import all_tools

    parsed = yaml.safe_load("tools:" + _default_tools_yaml())["tools"] or {}
    expected = {n for n, t in all_tools().items()
                if t.default_enabled and "group" in t.scope}
    assert set(parsed) == expected
    assert all(v == {"enabled": True} for v in parsed.values())
