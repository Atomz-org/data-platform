"""Tests for the eval layer.

The properties worth pinning are the ones whose failure would be silent. A
grader that quietly passes when a field is absent, a template that renders a
placeholder into a case verbatim, a discovery walk that reaches into a sister
project — none of these raise, and all of them produce a green suite that is
measuring nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pf.evals.case import AGENT_INPUTS, CaseError, discover, load_case, validate_case
from pf.evals.grade import MISSING, grade, resolve
from pf.evals.template import (
    Binding,
    TemplateError,
    load_template,
    render,
)
from pydantic import BaseModel


# ------------------------------------------------------------- fixtures ----
class Proposal(BaseModel):
    metric_name: str
    metric_type: str
    expr: str = ""


class Proposals(BaseModel):
    proposals: list[Proposal]
    summary: str = ""


def _case(tmp_path: Path, **overrides) -> Path:
    body = {
        "name": "c", "agent": "freshness_triage",
        "input": {"monitor_rows": []}, "expect": {"ignorable": True},
    }
    body.update(overrides)
    path = tmp_path / "c.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


# ---------------------------------------------------------------- grading --
def test_a_missing_field_fails_rather_than_passing() -> None:
    """The failure that would make the whole suite worthless. An expectation on a
    field the response does not have must fail, not be skipped."""
    failures = grade(Proposals(proposals=[]), {"nonexistent": "x"})
    assert len(failures) == 1
    assert failures[0].actual is MISSING


def test_a_refusal_fails_every_expectation() -> None:
    """A refusal arrives as None. Passing it would hide a prompt that has become
    unanswerable — the single most important thing an eval can report."""
    failures = grade(None, {"ignorable": True, "severity": "info"})
    assert len(failures) == 2


def test_list_paths_map_over_the_collection() -> None:
    parsed = Proposals(proposals=[Proposal(metric_name="a", metric_type="ratio"),
                                  Proposal(metric_name="b", metric_type="simple")])
    assert resolve(parsed, "proposals[].metric_type") == ["ratio", "simple"]


def test_a_scalar_on_a_list_path_requires_every_element_to_match() -> None:
    parsed = Proposals(proposals=[Proposal(metric_name="a", metric_type="ratio"),
                                  Proposal(metric_name="b", metric_type="simple")])
    assert grade(parsed, {"proposals[].metric_type": "ratio"})


def test_any_requires_only_one_element_to_match() -> None:
    parsed = Proposals(proposals=[Proposal(metric_name="a", metric_type="ratio"),
                                  Proposal(metric_name="b", metric_type="simple")])
    assert not grade(parsed, {"proposals[].metric_type": {"any": {"equals": "ratio"}}})


def test_references_only_catches_an_invented_column() -> None:
    """The hallucination check. A schema-valid metric over a column that does not
    exist reads perfectly and breaks at compile time."""
    parsed = Proposals(proposals=[Proposal(metric_name="m", metric_type="simple",
                                           expr="sum(discount_amount)")])
    failures = grade(parsed, {"proposals[].expr":
                              {"references_only": ["line_amount", "quantity"]}})
    assert failures and "discount_amount" in str(failures[0])


def test_references_only_ignores_sql_grammar() -> None:
    """`sum` and `case` are grammar, not column names. Flagging them would make
    the check unusable on any real expression."""
    parsed = Proposals(proposals=[Proposal(metric_name="m", metric_type="simple",
                                           expr="sum(case when quantity > 0 then 1 else 0 end)")])
    assert not grade(parsed, {"proposals[].expr": {"references_only": ["quantity"]}})


def test_an_unknown_matcher_is_an_error_not_a_pass() -> None:
    """A typo'd matcher silently passing is how a case stops testing anything."""
    with pytest.raises(ValueError, match="unknown matcher"):
        grade(Proposals(proposals=[]), {"summary": {"contins": "x"}})


# ------------------------------------------------------------ case loading --
def test_a_case_naming_an_unknown_agent_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(CaseError, match="agent"):
        load_case(_case(tmp_path, agent="nope"))


def test_a_case_missing_an_input_key_is_rejected(tmp_path: Path) -> None:
    """A case missing `lineage` would run with an empty neighbourhood and grade a
    question the agent was never asked."""
    with pytest.raises(CaseError, match="needs input keys"):
        load_case(_case(tmp_path, agent="test_failure_triage",
                        input={"failures": []}))


def test_a_case_with_a_stray_input_key_is_rejected(tmp_path: Path) -> None:
    """Catches the typo that would otherwise be silently dropped at call time."""
    with pytest.raises(CaseError, match="takes no input"):
        load_case(_case(tmp_path, input={"monitor_rows": [], "extra": 1}))


def test_every_dispatchable_agent_has_declared_inputs() -> None:
    from pf.evals.runner import DISPATCH

    assert set(DISPATCH) == set(AGENT_INPUTS)


# --------------------------------------------------------------- discovery --
def test_discovery_never_reads_a_sister(tmp_path: Path) -> None:
    """The rule the whole repository is organised around. Discovery is given one
    group and one project and must not reach past them."""
    root = tmp_path
    (root / "platform" / "toolkits").mkdir(parents=True)
    for group, project in (("acme", "acme-eu"), ("acme", "acme-us"), ("globex", "globex-eu")):
        d = root / "groups" / group / "projects" / project / "evals" / "cases"
        d.mkdir(parents=True)
        (d / "c.json").write_text(json.dumps({
            "name": f"{project}_case", "agent": "freshness_triage",
            "input": {"monitor_rows": []}, "expect": {"ignorable": True}}), encoding="utf-8")

    found = {c.name for c in discover(root, "acme", "acme-eu")}
    assert found == {"acme-eu_case"}


def test_templates_are_not_discovered_as_cases(tmp_path: Path) -> None:
    """A template carries `{{bindings}}` and is not runnable. Loading one as a
    case would grade a question about a table called '{{mart.name}}'."""
    tdir = tmp_path / "platform" / "toolkits" / "k" / "evals" / "templates"
    tdir.mkdir(parents=True)
    (tdir / "t.json").write_text(json.dumps({
        "template": "t", "agent": "freshness_triage", "requires": {},
        "input": {"monitor_rows": []}, "expect": {"ignorable": True}}), encoding="utf-8")

    assert discover(tmp_path, None, None) == []


def test_duplicate_case_names_are_rejected(tmp_path: Path) -> None:
    root = tmp_path
    (root / "platform" / "toolkits").mkdir(parents=True)
    for tier in ("evals", "projects/p/evals/cases"):
        d = root / "groups" / "g" / tier
        d.mkdir(parents=True)
        (d / "c.json").write_text(json.dumps({
            "name": "same", "agent": "freshness_triage",
            "input": {"monitor_rows": []}, "expect": {"ignorable": True}}), encoding="utf-8")

    with pytest.raises(CaseError, match="duplicate"):
        discover(root, "g", "p")


# --------------------------------------------------------------- templates --
def _template(tmp_path: Path, **overrides) -> Path:
    body = {
        "template": "t", "agent": "freshness_triage",
        "requires": {"mart": "mart"},
        "input": {"monitor_rows": [{"resource": "{{mart.name}}"}]},
        "expect": {"ignorable": True},
    }
    body.update(overrides)
    path = tmp_path / "t.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def test_a_template_using_an_undeclared_binding_is_rejected(tmp_path: Path) -> None:
    """Without this the template renders `{{other.name}}` into the case verbatim,
    and the case runs, asking about a table by that literal name."""
    with pytest.raises(TemplateError, match="does not require"):
        load_template(_template(tmp_path,
                                input={"monitor_rows": [{"resource": "{{other.name}}"}]}))


def test_a_template_with_an_unknown_selector_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(TemplateError, match="unknown selector"):
        load_template(_template(tmp_path, requires={"mart": "galaxy"}))


def test_rendering_substitutes_real_names(tmp_path: Path) -> None:
    tpl = load_template(_template(tmp_path))
    out = render(tpl, {"mart": Binding(name="fct_orders")})
    assert out["input"]["monitor_rows"][0]["resource"] == "fct_orders"
    assert "{{" not in json.dumps(out)


def test_identifiers_interpolate_as_a_list_not_a_string(tmp_path: Path) -> None:
    """`references_only` needs a real list. Rendering it as a string would make
    the hallucination check compare against the characters of a repr."""
    tpl = load_template(_template(
        tmp_path,
        expect={"summary": {"references_only": "{{mart.identifiers}}"}}))
    out = render(tpl, {"mart": Binding(name="m", identifiers=("m", "amount"))})
    assert out["expect"]["summary"]["references_only"] == ["m", "amount"]


def test_a_rendered_template_is_a_valid_case(tmp_path: Path) -> None:
    tpl = load_template(_template(tmp_path))
    out = render(tpl, {"mart": Binding(name="fct_orders")})
    assert validate_case(out, origin="rendered").agent == "freshness_triage"


def test_shipped_templates_all_load_and_render() -> None:
    """The toolkits' own templates. A malformed one is a platform defect with
    project-shaped consequences: the error surfaces in someone else's project,
    against a file they did not write."""
    from pf import obs
    from pf.evals.template import discover_templates

    templates = discover_templates(obs.repo_root())
    assert templates, "no toolkit ships eval templates"

    for tpl in templates:
        bindings = {name: Binding(name=f"{name}_model", grain="one row per thing",
                                  columns="a(int)", column="a",
                                  identifiers=(f"{name}_model", "a"))
                    for name in tpl.requires}
        rendered = render(tpl, bindings)
        assert "{{" not in json.dumps(rendered), f"{tpl.name} left a placeholder"
        validate_case(rendered, origin=str(tpl.source))


# ---------------------------------------------------------------- contract --
def test_contract_checks_run_without_a_credential() -> None:
    """The whole point of the tier: it must be runnable in CI, on a machine with
    no API key, and still catch a request shape the model would reject."""
    from pf import obs
    from pf.evals import run_contract

    results = run_contract(obs.repo_root(), "acme", "acme-eu")
    assert results
    by_name = {r.name: r for r in results}
    assert by_name["requests_are_accepted_by_their_model"].outcome == "pass"
    assert by_name["cached_prefix_is_byte_stable"].outcome == "pass"
