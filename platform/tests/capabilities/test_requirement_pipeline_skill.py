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
plan_commits = _load("plan_commits")
PER_ENTITY = SKILL_DIR / "assets" / "spec.per-entity.example.yaml"
COMMODITY_INDIA = REPO_ROOT / "groups" / "commodity" / "projects" / "commodity-india"


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
    (lambda s: s["metrics"][0].pop("unit"), "unit required"),
    (lambda s: s["metrics"][2].update(unit="lots"), "unit 'lots'"),
    (lambda s: s["metrics"][0].update(unit="count"), "measures money column 'amount_usd'"),
    (lambda s: s["metrics"][1].update(label="gross revenue"), "already used"),
    (lambda s: s["metrics"].append(dict(s["metrics"][2], label="Other")), "defined twice"),
    (lambda s: s["models"]["marts"].append(dict(s["models"]["marts"][0])), "defined twice"),
    (lambda s: s["sources"][0]["resources"][0].update(currency="dollars"), "not an ISO 4217 code"),
    (lambda s: s["reports"][0].update(per_entity="Store Id"), "per_entity names the dimension"),
    (lambda s: s["schedule"].update(per_entity={"by": "store_id"}), "catalogue: the seed or model"),
    (lambda s: s["schedule"].update(cron=None, per_entity={"by": "store_id", "catalogue": "stores"}),
     "still needs schedule.cron"),
    (lambda s: s["schedule"].update(per_entity={"by": "store_id", "catalogue": "stores", "stagger": "soon"}),
     "stagger"),
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


def test_a_constant_currency_satisfies_the_money_rule_as_annotate_does() -> None:
    """`pf.ontology.annotate(currency=...)` is how a single-currency source
    declares its amounts, and `validate_annotations` accepts it — so must the
    spec, or a correct spec is refused one phase early."""
    def single_currency(s):
        roles = s["sources"][0]["resources"][0]["roles"]
        roles.pop("currency")
        s["sources"][0]["resources"][0]["currency"] = "USD"
    assert _errors_after(single_currency) == []


def test_summing_a_level_over_time_is_warned() -> None:
    def balance(s):
        s["metrics"][0]["measure"]["expr"] = "account_balance"
    assert any("non_additive" in w for w in _warnings_after(balance))
    def declared(s):
        balance(s)
        s["metrics"][0]["measure"]["non_additive"] = {"dimension": "placed_at", "window": "last"}
    assert not any("non_additive" in w for w in _warnings_after(declared))


def test_a_label_an_existing_metric_already_uses_is_refused(tmp_path: Path) -> None:
    project = tmp_path / "example" / "projects" / "example-retail"
    (project / "transform" / "models" / "semantic").mkdir(parents=True)
    (project / "transform" / "models" / "semantic" / "m.yml").write_text(
        "metrics:\n  - {name: revenue_gross, label: Gross Revenue, type: simple}\n")
    errors = validate_spec.validate(_example(), project).errors
    assert any("label 'Gross Revenue' is already used" in e for e in errors), errors


def test_a_per_entity_spec_plans_one_job_per_entity_and_templated_pages() -> None:
    spec = copy.deepcopy(_example())
    spec["schedule"]["per_entity"] = {"by": "channel", "catalogue": "channels", "stagger": "3m",
                                      "start_paused": ["wholesale"]}
    spec["reports"][0]["per_entity"] = "channel"
    rep = validate_spec.validate(spec)
    assert rep.errors == [], rep.errors
    assert any("created in Phase 4" in w for w in rep.warnings)   # the catalogue does not exist yet
    assert any(p["layer"] == "orchestration" for p in rep.plan)
    assert 10 in validate_spec.phases(rep, spec)
    assert "reporting/pages/online-revenue/[channel].md" in validate_spec.trace(spec)


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
    assert "add-anomaly-tests" in validate_spec.skills_for(5, spec)         # freshness is the source's
    assert "add-anomaly-tests" not in validate_spec.skills_for(7, spec)     # …never the mart's
    spec["models"]["marts"][0]["monitors"] = ["daily order volume"]
    assert "add-anomaly-tests" in validate_spec.skills_for(7, spec)
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


def _project_with_staging(tmp_path: Path) -> Path:
    project = tmp_path / "example" / "projects" / "example-retail"
    (project / "transform" / "models" / "staging" / "shop_api").mkdir(parents=True)
    (project / "transform" / "models" / "staging" / "shop_api" / "stg_shop_api__orders.sql").write_text("select 1")
    return project


@pytest.mark.parametrize("landed_by", ["annotations", "dbt_sources"])
def test_the_plan_reuses_what_a_project_already_has(tmp_path: Path, landed_by: str) -> None:
    project = _project_with_staging(tmp_path)
    if landed_by == "annotations":
        (project / "contracts").mkdir()
        (project / "contracts" / "annotations.yaml").write_text(
            "version: 2\nresources:\n  - {resource: orders, source: shop_api, concept: Order}\n")
    else:
        (project / "transform" / "models" / "staging" / "shop_api" / "_shop_api__sources.yml").write_text(
            "version: 2\nsources:\n  - name: shop_api\n    tables:\n      - name: orders\n")
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


def test_staging_alone_does_not_mean_the_source_has_landed(tmp_path: Path) -> None:
    """Raw is planned from what the project lands, not from staging: a staging
    model with no pipeline behind it still needs Phase 4."""
    project = _project_with_staging(tmp_path)
    rep = validate_spec.validate(_example(), project)
    actions = {(p["layer"], p["name"]): p["action"] for p in rep.plan}
    assert actions[("raw", "shop_api.orders")] == "create"
    assert actions[("staging", "stg_shop_api__orders")] == "reuse"
    assert 4 in validate_spec.phases(rep, _example())


def test_a_relative_project_dir_is_resolved_before_the_target_check(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "example" / "projects" / "example-retail"
    project.mkdir(parents=True)
    monkeypatch.chdir(project)
    errors = validate_spec.validate(_example(), Path()).errors
    assert not any(e.startswith("target") for e in errors), errors


def test_an_unreadable_spec_is_an_error_not_a_traceback(tmp_path: Path, capsys) -> None:
    bad = tmp_path / "spec.yaml"
    bad.write_text("spec_version: 1\nrequirement: [unclosed\n")
    assert validate_spec.main([str(bad)]) == 1
    assert "✗" in capsys.readouterr().out


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


# ------------------------------------------------------------------- fetch ----
def test_credentials_are_never_sent_over_plain_http() -> None:
    with pytest.raises(SystemExit, match="non-https"):
        confluence_fetch._get("http://wiki.example.com/rest/api/content/1")


def test_a_redirect_is_refused_rather_than_followed_with_credentials() -> None:
    """urllib copies Authorization onto a redirected request; the fetcher's
    opener must refuse the redirect instead."""
    import io
    import urllib.error
    import urllib.request

    handler = next(h for h in confluence_fetch._OPENER.handlers
                   if isinstance(h, urllib.request.HTTPRedirectHandler))
    req = urllib.request.Request("https://x.atlassian.net/wiki/api/v2/pages/1",
                                 headers={"Authorization": "Basic c2VjcmV0"})
    with pytest.raises(urllib.error.HTTPError, match="refusing redirect"):
        handler.redirect_request(req, io.BytesIO(), 302, "Found", {}, "http://evil.example.com/")


# ------------------------------------------------------ the group and tiers ----
def _per_entity() -> dict:
    return yaml.safe_load(PER_ENTITY.read_text(encoding="utf-8"))


def test_the_per_entity_example_is_valid_on_its_own() -> None:
    rep = validate_spec.validate(_per_entity())
    assert rep.errors == [] and rep.blocking == []


def _unbuilt_commodity(tmp_path: Path) -> Path:
    """A commodity family as the MCX requirement found it: two classes, a
    conformance test holding staging and intermediate identical, a group skill,
    a sister, and a project whose seed script does not know the exchange yet.

    Written here rather than read from the checkout: the real commodity-india
    is the project the example was built into, so once that build lands the
    live tree no longer shows what planning a fresh build looks like."""
    group = tmp_path / "commodity"
    (group / "ontology").mkdir(parents=True)
    (group / "ontology" / "extension.yaml").write_text(
        "classes:\n  Commodity: {identity: commodity_id}\n  Market: {identity: market_code}\n")
    (group / "shared" / "python" / "tests").mkdir(parents=True)
    (group / "shared" / "python" / "tests" / "test_conformed.py").write_text(
        'CONFORMED = ("models/intermediate", "models/staging")\n')
    (group / ".claude" / "skills" / "price-arithmetic").mkdir(parents=True)
    (group / ".claude" / "skills" / "price-arithmetic" / "SKILL.md").write_text("---\nname: price-arithmetic\n---\n")
    (group / "projects" / "commodity-us").mkdir(parents=True)
    project = group / "projects" / "commodity-india"
    (project / "src" / "commodity_india").mkdir(parents=True)
    (project / "src" / "commodity_india" / "seed.py").write_text("SOURCES = ['futures_prices', 'fx_rates']\n")
    (project / "transform" / "models" / "marts").mkdir(parents=True)
    return project


def test_the_per_entity_example_plans_a_fresh_build_across_tiers(tmp_path: Path) -> None:
    """The multi-entity build crosses tiers: two group-tier classes and a
    conformance exemption, planned once each, no recce baseline (nothing
    existing is diffable), and the family's own skills surfaced."""
    spec = _per_entity()
    rep = validate_spec.validate(spec, _unbuilt_commodity(tmp_path))
    assert rep.errors == [], rep.errors
    layers = [(p["layer"], p["name"]) for p in rep.plan]
    assert ("group", "ontology: ExchangeContract") in layers
    assert layers.count(("group", "ontology: ExchangeContract")) == 1
    assert ("group", "conformance_exemption: models/staging/mcx") in layers
    phases = validate_spec.phases(rep, spec)
    assert 3 not in phases and 10 in phases
    assert rep.group_skills == ["price-arithmetic"], "the group's own skills are listed for Phase 0"
    assert any("seed.py does not name it" in w for w in rep.warnings)


def test_a_new_source_under_a_conformed_path_is_warned_without_its_exemption(tmp_path: Path) -> None:
    spec = _per_entity()
    spec["group_changes"] = [g for g in spec["group_changes"] if g["kind"] != "conformance_exemption"]
    warnings = validate_spec.validate(spec, _unbuilt_commodity(tmp_path)).warnings
    assert any("conformed across sisters" in w and "models/staging/mcx" in w for w in warnings), warnings


@pytest.mark.skipif(not (COMMODITY_INDIA / "transform" / "models" / "staging" / "mcx").is_dir(),
                    reason="the example's build has not landed in this checkout")
def test_replanning_a_landed_build_reuses_it_rather_than_redoing_it() -> None:
    """Run again against the project it was built into, the same spec must not
    redesign what landed: the classes it added are in the group ontology now
    (reuse, with a nudge to say `exists: true`), the sources it loaded are
    reused, and nothing it declared is an error."""
    spec = _per_entity()
    rep = validate_spec.validate(spec, COMMODITY_INDIA)
    assert rep.errors == [], rep.errors
    action = {(p["layer"], p["name"]): p["action"] for p in rep.plan}
    assert action[("group", "ontology: ExchangeContract")] == "reuse"
    assert action[("group", "ontology: ContractSession")] == "reuse"
    assert action[("raw", "mcx.futures_bhavcopy")] == "reuse"
    assert action[("staging", "stg_mcx__futures_bhavcopy")] == "reuse"
    assert any("already a class in the group ontology" in w for w in rep.warnings)
    assert not any("not in the ontology" in w for w in rep.warnings)


@pytest.mark.parametrize("mutate, expected", [
    (lambda s: s["concepts"][2].pop("tier"), "a new concept needs tier"),
    (lambda s: s["concepts"][2].update(tier="platform"), "platform-tier class is a platform change"),
    (lambda s: s["group_changes"][0].pop("why"), "why required"),
    (lambda s: s["group_changes"][0].update(kind="rewrite"), "kind must be one of"),
    (lambda s: s["metrics"][0]["measure"].update(expr="flagship_close_price"), "is a unit_price"),
])
def test_the_group_tier_is_changed_only_on_purpose(mutate, expected: str) -> None:
    spec = _per_entity()
    mutate(spec)
    errors = validate_spec.validate(spec).errors
    assert any(expected in e for e in errors), errors


def test_a_new_project_is_scaffolded_only_when_asked(tmp_path: Path) -> None:
    group = tmp_path / "example"
    (group / "projects").mkdir(parents=True)
    missing = group / "projects" / "example-retail"
    assert any("does not exist" in e for e in validate_spec.validate(_example(), missing).errors)

    spec = _example()
    spec["target"]["create"] = True
    rep = validate_spec.validate(spec, missing)
    assert rep.errors == [], rep.errors
    assert {"layer": "project", "name": "example/example-retail", "action": "create"} in rep.plan
    assert "scaffold-project" in validate_spec.skills_for(0, spec)

    missing.mkdir()
    assert any("already exists" in e for e in validate_spec.validate(spec, missing).errors)


def test_a_new_group_is_a_decision_not_a_side_effect(tmp_path: Path) -> None:
    project = tmp_path / "example" / "projects" / "example-retail"
    spec = _example()
    spec["target"]["create"] = True
    assert any("does not exist" in e and "new_group" in e for e in validate_spec.validate(spec, project).errors)
    spec["target"]["new_group"] = True
    rep = validate_spec.validate(spec, project)
    assert rep.errors == [] and any("pf new-group" in w for w in rep.warnings)


def test_the_family_is_read_for_reuse_and_registration(tmp_path: Path) -> None:
    group = tmp_path / "example"
    project = group / "projects" / "example-retail"
    (project / "src" / "example_retail").mkdir(parents=True)
    (project / "src" / "example_retail" / "seed.py").write_text("run_source(wh, other_feed)\n")
    (group / "shared" / "python" / "src" / "example_shared").mkdir(parents=True)
    (group / "shared" / "python" / "src" / "example_shared" / "shop_api.py").write_text("")
    (group / "shared" / "transform" / "seeds").mkdir(parents=True)
    (group / "shared" / "transform" / "seeds" / "channels.csv").write_text("channel\n")
    spec = _example()
    spec["schedule"]["per_entity"] = {"by": "channel", "catalogue": "channels"}
    warnings = validate_spec.validate(spec, project).warnings
    assert any("group already ships a connector" in w for w in warnings), warnings
    assert any("seed.py does not name it" in w for w in warnings), warnings
    assert not any("catalogue 'channels'" in w for w in warnings), "a shared seed is a catalogue already"


@pytest.mark.parametrize("mutate, expected", [
    (lambda s: s["models"]["marts"][0].update(access="public"), "access: public is for marts read outside"),
    (lambda s: s["models"]["marts"][0].pop("columns"), "no column roles"),
    (lambda s: s["sources"][0]["resources"][0].pop("incremental"), "no incremental cursor"),
])
def test_what_the_owning_skills_require_is_warned(mutate, expected: str) -> None:
    assert any(expected in w for w in _warnings_after(mutate))


def test_a_group_change_alone_does_not_ask_for_a_data_baseline() -> None:
    spec = _per_entity()
    rep = validate_spec.validate(spec)
    assert not validate_spec.modifies_data(rep)
    assert "recce-review" not in validate_spec.skills_for(13, spec, validate_spec.modifies_data(rep))


# ----------------------------------------------------------------- delivery ----
BUILD = [
    "groups/g/projects/p/okf/metrics/m1.md",
    "groups/g/projects/p/transform/models/marts/area/fct_x.sql",
    "groups/g/projects/p/src/p/sources/feed.py",
    "groups/g/projects/p/tests/test_feed.py",
    "groups/g/projects/p/transform/models/staging/feed/stg_feed__rows.sql",
    "groups/g/projects/p/transform/models/intermediate/feed/int_feed__rolled.sql",
    "groups/g/projects/p/transform/models/marts/area/_area__semantic.yml",
    "groups/g/projects/p/src/p/defs/feed.py",
    "groups/g/projects/p/reporting/pages/feed/index.md",
    "groups/g/projects/p/reporting/pages/metrics/m1.md",
    "groups/g/projects/p/kg/graph.json",
    "groups/g/ontology/extension.yaml",
    "groups/g/projects/sister/okf/concepts/Thing.md",
    "groups/g/projects/p/HARNESS.md",
    "vendor/upstream",
    "groups/g/projects/p/data/p.duckdb",
    "uv.lock",
]


def test_commits_are_planned_in_pipeline_order() -> None:
    out = plan_commits.plan(BUILD, "g", "p")
    order = [s["title"] for s in out["slices"]]
    assert order == ["group tier", "sister bundles (generated)", "ingestion", "staging (generated)",
                     "intermediate", "marts and tests", "semantic layer", "orchestration and docs",
                     "hand-written pages", "generated metric pages", "OKF bundle", "graph, MDL, catalogue"]
    assert out["maps"] == ["groups/g/projects/p/HARNESS.md"], "maps are regenerated per slice, never planned"
    assert set(out["refused"]) == {"vendor/upstream", "groups/g/projects/p/data/p.duckdb"}
    assert "uv.lock" in next(s for s in out["slices"] if s["title"] == "ingestion")["files"]


def test_every_slice_leaves_room_for_its_harness_maps() -> None:
    pages = [f"groups/g/projects/p/reporting/pages/metrics/m{i}.md" for i in range(40)]
    group = [f"groups/g/okf/concepts/C{i}.md" for i in range(20)]
    out = plan_commits.plan(pages + group, "g", "p")
    for s in out["slices"]:
        room = 3 if s["title"].startswith("group tier") else 1
        assert len(s["files"]) + room <= plan_commits.MAX_FILES, s
    assert out["slices"][0]["harness"] == "pf harness g"
    assert out["slices"][-1]["harness"] == "pf harness g p"


def test_porcelain_input_keeps_renames_and_drops_deletions() -> None:
    lines = [" M a/b.sql", "?? c/d.md", "R  old.sql -> new.sql", " D gone.sql", "D  gone2.sql"]
    assert plan_commits._porcelain(lines) == ["a/b.sql", "c/d.md", "new.sql"]


def test_a_row_shaped_criterion_is_proved_through_wren() -> None:
    """An acceptance criterion that asks for rows rather than a number has no
    metric to prove it, and the alternative — raw SQL against the warehouse —
    is exactly what `query` is forbidden from doing. Phase 9 routes it through
    the gated road, and Phase 12 checks the workspace `pf semantic mdl` just
    rewrote, so both places that print the routing agree."""
    assert "ask-through-wren" in validate_spec.SKILLS[9]
    assert "ask-through-wren" in validate_spec.SKILLS[12]
    text = SKILL_MAP.read_text(encoding="utf-8")
    phase9 = text.split("## Phase 9")[1].split("## Phase 10")[0]
    phase12 = text.split("## Phase 12")[1].split("## Phase 13")[0]
    assert "`ask-through-wren`" in phase9 and "pf tool wren query" in phase9
    assert "`ask-through-wren`" in phase12 and "pf tool wren check" in phase12
