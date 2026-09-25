"""The build-from-requirement skill, checked against the platform it drives.

The skill is an orchestration document: it names a `pf` command or a sibling
skill at every phase, and an agent does what it names. So its evidence is that
every command resolves in the CLI, every sibling skill it routes to exists, and
the two scripts it ships behave as the references promise — the validator
refuses the specs the skill says it refuses, and the Confluence converter keeps
the structure (tables, code macros, panels) that extraction depends on.
"""

from __future__ import annotations

import copy
import importlib.util
import re
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT

TOOLKIT = REPO_ROOT / "platform" / "toolkits" / "requirement-pipeline"
SKILL_DIR = TOOLKIT / "skills" / "build-from-requirement"
SKILL = SKILL_DIR / "SKILL.md"
EXAMPLE = SKILL_DIR / "assets" / "spec.example.yaml"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SKILL_DIR / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


validate_spec = _load("validate_spec")
confluence_fetch = _load("confluence_fetch")


def _text() -> str:
    return SKILL.read_text(encoding="utf-8")


def _example() -> dict:
    return yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))


def _cli() -> set[str]:
    from pf.cli import app

    names: set[str] = set()
    for c in app.registered_commands:
        names.add(c.name or c.callback.__name__.replace("_", "-"))
    for t in app.registered_groups:
        group = t.name or t.typer_instance.info.name or ""
        names.add(group)
        for c in t.typer_instance.registered_commands:
            names.add(f"{group} {c.name or c.callback.__name__.replace('_', '-')}")
        for sub in t.typer_instance.registered_groups:
            sub_name = sub.name or sub.typer_instance.info.name or ""
            names.add(f"{group} {sub_name}")
            for c in sub.typer_instance.registered_commands:
                names.add(f"{group} {sub_name} {c.name or c.callback.__name__.replace('_', '-')}")
    return names


# ------------------------------------------------------------ the document ----
def test_the_skill_is_addressable() -> None:
    assert _text().startswith("---\nname: build-from-requirement\n")


def _commands() -> set[str]:
    docs = [SKILL, *(SKILL_DIR / "references").glob("*.md")]
    found: set[str] = set()
    for doc in docs:
        for line in re.findall(r"`?(pf [a-z][\w -]*)", doc.read_text(encoding="utf-8")):
            found.add(" ".join(w for w in line.split() if not w.startswith(("<", "--", "`"))))
    return found


@pytest.mark.parametrize("command", sorted(_commands()))
def test_every_command_the_skill_names_exists(command: str) -> None:
    words = command.split()[1:]
    known = _cli()
    for depth in (3, 2, 1):
        if len(words) >= depth and " ".join(words[:depth]) in known:
            return
    pytest.fail(f"`{command}` is in the skill and not in the CLI")


TOOLKITS = REPO_ROOT / "platform" / "toolkits"
SKILL_MAP = SKILL_DIR / "references" / "skill-map.md"


def _toolkit_skills() -> set[str]:
    return {p.parent.name for p in TOOLKITS.glob("*/skills/*/SKILL.md")} - {"build-from-requirement"}


def _helpers() -> set[str]:
    """Everything a phase may route to: toolkit skills, the power-tools
    subagents, the power-tools slash commands, and toolkit names themselves."""
    power = TOOLKITS / "power-tools"
    return (_toolkit_skills()
            | {p.stem for p in (power / "agents").glob("*.md")}
            | {p.stem for p in (power / "commands").glob("*.md")}
            | {p.name for p in TOOLKITS.iterdir() if p.is_dir()})


@pytest.mark.parametrize("doc", [SKILL, SKILL_MAP], ids=lambda p: p.name)
def test_every_skill_it_routes_to_exists(doc: Path) -> None:
    """A phase that names a skill nobody ships is a phase the agent improvises."""
    text = doc.read_text(encoding="utf-8")
    named = set(re.findall(r"`/?([a-z]+(?:-[a-z]+)+)`", text))
    not_skills = {"build-from-requirement", "requirement-pipeline"}
    missing = {n for n in named - not_skills if n not in _helpers()}
    assert not missing, f"{doc.name} routes to skills that do not exist: {sorted(missing)}"


def test_every_toolkit_skill_has_a_place_in_the_map() -> None:
    """The point of this skill is to use the toolkits rather than re-derive
    them, so each toolkit skill is either routed to by some phase or named in
    the out-of-scope hand-back. A skill added to a toolkit later fails here
    until someone decides where it belongs."""
    # single-word names too (`query`), which the existence check cannot tell from prose
    mapped = set(re.findall(r"`/?([a-z]+(?:-[a-z]+)*)`", SKILL_MAP.read_text(encoding="utf-8")))
    unplaced = _toolkit_skills() - mapped
    assert not unplaced, f"toolkit skills skill-map.md neither routes to nor hands back: {sorted(unplaced)}"


def test_the_validator_routes_only_to_shipped_helpers() -> None:
    routed = {s for names in validate_spec.SKILLS.values() for s in names}
    routed |= set(validate_spec.KIND_SKILL.values()) | set(validate_spec.RULE_TESTS.values())
    assert routed <= _helpers(), sorted(routed - _helpers())
    assert set(validate_spec.KIND_SKILL) == validate_spec.KINDS


def test_every_file_it_references_ships() -> None:
    for rel in re.findall(r"`((?:references|assets|scripts)/[\w./-]+)`", _text()):
        assert (SKILL_DIR / rel).is_file(), f"{rel} is named in the skill and not shipped"


def test_phase_numbers_agree_with_the_validator() -> None:
    headings = {int(n): title for n, title in re.findall(r"^## Phase (\d+) — (.+)$", _text(), re.M)}
    assert sorted(headings) == sorted(validate_spec.PHASES.values())


# ---------------------------------------------------------------- validator ----
def test_the_example_spec_is_valid() -> None:
    rep = validate_spec.validate(_example())
    assert rep.errors == []
    assert rep.blocking == []   # its one blocking question is answered


def test_the_template_is_refused_until_filled() -> None:
    rep = validate_spec.validate(yaml.safe_load((SKILL_DIR / "assets" / "spec-template.yaml").read_text()))
    assert any(e.startswith("target.group") for e in rep.errors)
    assert any(e.startswith("acceptance") for e in rep.errors)


def _errors_after(mutate) -> list[str]:
    spec = copy.deepcopy(_example())
    mutate(spec)
    return validate_spec.validate(spec).errors


@pytest.mark.parametrize("mutate, expected", [
    (lambda s: s["sources"][0]["resources"][0]["roles"].pop("currency"), "money_amount needs a sibling currency_code"),
    (lambda s: s["sources"][0]["resources"][0]["roles"].update(customer_id="natural_key"), "exactly one natural_key"),
    (lambda s: s["sources"][0]["resources"][0].pop("primary_key"), "merge needs primary_key"),
    (lambda s: s["models"]["intermediate"][0].update(name="orders_clean"), "int_<entity>__<verb>"),
    (lambda s: s["models"]["marts"][0].update(grain=None), "grain required"),
    (lambda s: s["metrics"][3].update(numerator="missing_metric"), "numerator 'missing_metric'"),
    (lambda s: s["metrics"][0]["measure"].update(expr="amount_usd / 2"), "avg(ratio)"),
    (lambda s: s["business_rules"][0].update(implemented_in=[]), "implemented_in is empty"),
    (lambda s: s["business_rules"][0].pop("test"), "a rule nobody checks"),
    (lambda s: s["reports"][0]["metrics"].append("churn"), "metric 'churn'"),
    (lambda s: s.update(acceptance=[]), "at least one criterion"),
    (lambda s: s["sources"][0]["connection"].update(api_token="abc123"), "credential"),
    (lambda s: s["requirement"].update(summary="call with Bearer abcdefghijkl"), "live credential"),
])
def test_the_validator_refuses_what_the_reference_says_it_refuses(mutate, expected: str) -> None:
    errors = _errors_after(mutate)
    assert any(expected in e for e in errors), errors


def test_a_metric_filter_proves_only_a_metric_rule() -> None:
    errors = _errors_after(lambda s: s["business_rules"][0].update(test={"type": "metric_filter"}))
    assert any("metric_filter proves only" in e for e in errors), errors


def _warnings_after(mutate) -> list[str]:
    spec = copy.deepcopy(_example())
    mutate(spec)
    rep = validate_spec.validate(spec)
    assert rep.errors == [], rep.errors
    return rep.warnings


def test_an_anomaly_monitor_alone_is_warned_not_accepted_silently() -> None:
    warnings = _warnings_after(lambda s: s["business_rules"][0].update(test={"type": "anomaly_monitor"}))
    assert any("choose-a-test" in w for w in warnings), warnings


def test_foreign_dialect_sql_routes_to_the_porting_skill() -> None:
    def add_sql(s):
        s["business_rules"][2]["reference_sql"] = {"dialect": "snowflake", "sql": "select iff(a, b, c)"}
    assert any("port-snowflake-sql" in w for w in _warnings_after(add_sql))
    spec = copy.deepcopy(_example())
    add_sql(spec)
    assert "port-snowflake-sql" in validate_spec.skills_for(6, spec)
    spec["business_rules"][2]["reference_sql"]["dialect"] = "duckdb"
    assert not any("port-snowflake-sql" in w for w in validate_spec.validate(spec).warnings)


def test_routing_follows_what_the_spec_contains() -> None:
    spec = copy.deepcopy(_example())
    assert "create-rest-pipeline" in validate_spec.skills_for(4, spec)
    assert "secrets-auditor" in validate_spec.skills_for(4, spec)          # it has a secret_ref
    assert {"add-tests", "add-unit-test"} <= set(validate_spec.skills_for(6, spec))  # BR-1, BR-3
    assert "add-anomaly-tests" in validate_spec.skills_for(7, spec)         # the source has freshness
    spec["sources"][0]["kind"] = "filesystem"
    assert {"create-filesystem-pipeline", "read-file"} <= set(validate_spec.skills_for(4, spec))
    assert "create-rest-pipeline" not in validate_spec.skills_for(4, spec)


def test_the_diff_review_runs_only_when_something_existing_changes() -> None:
    """Recce needs a baseline from before the change; a pure create has none to diff."""
    spec = _example()
    assert "recce-review" not in validate_spec.skills_for(13, spec, modifying=False)
    assert {"recce-review", "impact-verifier"} <= set(validate_spec.skills_for(13, spec, modifying=True))
    assert "recce-review" in validate_spec.SKILLS[3]


def test_an_unanswered_blocking_question_blocks() -> None:
    spec = copy.deepcopy(_example())
    spec["open_questions"][0]["answer"] = None
    rep = validate_spec.validate(spec)
    assert rep.errors == [] and len(rep.blocking) == 1


def test_the_plan_reuses_what_a_project_already_has(tmp_path: Path) -> None:
    project = tmp_path / "example" / "projects" / "example-retail"
    (project / "transform" / "models" / "staging" / "shop_api").mkdir(parents=True)
    (project / "transform" / "models" / "staging" / "shop_api" / "stg_shop_api__orders.sql").write_text("select 1")
    (project / "transform" / "models" / "semantic").mkdir()
    (project / "transform" / "models" / "semantic" / "m.yml").write_text(
        "metrics:\n  - {name: gross_revenue, type: simple}\n")
    spec = _example()
    spec["metrics"] = [m for m in spec["metrics"] if m["name"] != "gross_revenue"]
    rep = validate_spec.validate(spec, project)
    assert rep.errors == [], rep.errors
    actions = {(p["layer"], p["name"]): p["action"] for p in rep.plan}
    assert actions[("raw", "shop_api.orders")] == "reuse"
    assert actions[("staging", "stg_shop_api__orders")] == "reuse"
    assert actions[("marts", "fct_orders")] == "create"
    phases = validate_spec.phases(rep, spec)
    assert 4 not in phases and 5 not in phases and 7 in phases


def test_the_spec_must_target_the_project_it_is_checked_against(tmp_path: Path) -> None:
    other = tmp_path / "example" / "projects" / "someone-else"
    other.mkdir(parents=True)
    assert any(e.startswith("target") for e in validate_spec.validate(_example(), other).errors)


# ---------------------------------------------------------------- converter ----
STORAGE = """
<h2>KPIs</h2>
<table><tbody><tr><th>KPI</th><th>Formula</th></tr>
<tr><td><p>Net revenue</p></td><td>sum(amount) | completed</td></tr></tbody></table>
<ac:structured-macro ac:name="warning"><ac:rich-text-body><p>Excludes tests</p></ac:rich-text-body></ac:structured-macro>
<ul><li>one<ul><li>nested</li></ul></li><li>two</li></ul>
<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">sql</ac:parameter>
<ac:plain-text-body><![CDATA[select * from t where a < b]]></ac:plain-text-body></ac:structured-macro>
"""


def test_the_converter_keeps_the_structure_extraction_reads() -> None:
    md = confluence_fetch.storage_to_markdown(STORAGE)
    assert "## KPIs" in md
    assert "| KPI | Formula |" in md and "| Net revenue | sum(amount) \\| completed |" in md
    assert "> **WARNING:**\n> Excludes tests" in md
    assert "- one\n  - nested\n- two" in md
    assert "```sql\nselect * from t where a < b\n```" in md


@pytest.mark.parametrize("ref, pid", [
    ("123456", "123456"),
    ("https://x.atlassian.net/wiki/spaces/FIN/pages/123456/Online+Revenue", "123456"),
    ("https://wiki.example.com/pages/viewpage.action?pageId=987", "987"),
])
def test_page_ids_are_read_from_every_url_shape(ref: str, pid: str) -> None:
    assert confluence_fetch.page_id_from(ref) == pid
