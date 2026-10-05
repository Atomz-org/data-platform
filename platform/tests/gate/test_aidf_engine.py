"""The governance engine end to end: gate, contract, validators, ledger, write.

Every branch must reach the chain, and reach it in the pairing the provenance
audit checks — so after every scenario here `pf.provenance.report` must still
say the ledger is intact and complete. The attacks: a payload that mutates, a
role writing where it may not, a target that escapes the project, a secret in
the rationale (which must be caught *and* must not end up in the ledger), a
run of rejections that must trip the breaker, and a breaker that must not
unlatch itself.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT
from pf.aidf.breaker import TOOL_METRIC, BudgetExceeded
from pf.aidf.engine import GovernanceEngine
from pf.aidf.schemas import GovernanceStatus
from pf.provenance import actions, approve, read_all, report

PAYLOAD = {
    "mart_name": "fct_orders",
    "metric_name": "gross_revenue",
    "aggregation_type": "SUM",
    "sql_definition": "SELECT SUM(amount) AS gross_revenue FROM fct_orders WHERE status = 'paid'",
    "dependent_columns": ["amount", "status"],
    "author_agent": "metric-gap-harvester",
}
ROLE = "metric-gap-harvester"
COLS = {"amount", "status", "customer_id"}


@pytest.fixture()
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A checkout with the real gate policy, one entity and an empty ledger."""
    for name in ("gate.yaml", "gate.capabilities.yaml"):
        shutil.copy(REPO_ROOT / name, tmp_path / name)
    (tmp_path / "platform").mkdir()
    pdir = tmp_path / "groups" / "g" / "projects" / "p"
    (pdir / "governance").mkdir(parents=True)
    (tmp_path / "groups" / "g" / "ontology").mkdir()
    monkeypatch.setenv("PF_AGENT", "test-agent")
    return tmp_path


def _overlay(repo: Path, doc: dict) -> None:
    (repo / "groups" / "g" / "projects" / "p" / "governance" / "aidf.yaml").write_text(yaml.safe_dump(doc))


def _engine(repo: Path) -> GovernanceEngine:
    return GovernanceEngine(repo, "g", "p")


def _audit_is_clean(repo: Path) -> None:
    rep = report(repo)
    assert rep.intact, rep.breaks
    assert rep.ok, [f.detail for f in rep.findings if f.level == "fail"]


# ------------------------------------------------------------------ PASS --

def test_pass_writes_the_record_after_the_chain(repo: Path) -> None:
    out = _engine(repo).evaluate(json.dumps(PAYLOAD), role=ROLE, catalog_columns=COLS)
    assert out.status is GovernanceStatus.PASS and out.ok and out.written
    written = repo / "groups" / "g" / "projects" / "p" / "governance" / "metrics" / "fct_orders" / "gross_revenue.json"
    assert written.exists()
    doc = json.loads(written.read_text())
    assert doc["metric_name"] == "gross_revenue" and doc["status"] == "provisional"

    stages = actions(repo)[out.action_id]
    assert set(stages) == {"intent", "decision", "execution"}
    assert stages["decision"].payload["verdict"] == "allow"
    assert stages["execution"].payload["status"] == "ok"
    assert stages["execution"].payload["aidf_status"] == "PASS"
    assert stages["intent"].payload["payload_sha256"] and "sql_definition" not in json.dumps(stages["intent"].payload)
    assert out.chain_seq == stages["execution"].seq and out.chain_hash == stages["execution"].hash
    _audit_is_clean(repo)


def test_no_write_still_records(repo: Path) -> None:
    out = _engine(repo).evaluate(PAYLOAD, role=ROLE, catalog_columns=COLS, write=False)
    assert out.ok and not out.written
    assert not (repo / "groups" / "g" / "projects" / "p" / "governance" / "metrics").exists()
    assert actions(repo)[out.action_id]["execution"].payload["written"] is False


# ---------------------------------------------------------------- REJECT --

def test_mutating_sql_is_rejected_and_recorded(repo: Path) -> None:
    bad = {**PAYLOAD, "sql_definition": "DROP TABLE fct_orders; SELECT 1"}
    out = _engine(repo).evaluate(bad, role=ROLE, catalog_columns=COLS)
    assert out.status is GovernanceStatus.REJECT
    assert {f.code for f in out.findings} & {"multiple_statements", "mutation"}
    assert not (repo / "groups" / "g" / "projects" / "p" / "governance" / "metrics").exists()
    st = actions(repo)[out.action_id]
    assert st["decision"].payload["verdict"] == "deny" and st["decision"].payload["rule"] == "aidf:sql_ast"
    assert st["execution"].payload["status"] == "blocked" and st["execution"].payload["aidf_status"] == "REJECT"
    _audit_is_clean(repo)


def test_hallucinated_column_is_rejected(repo: Path) -> None:
    bad = {**PAYLOAD, "sql_definition": "SELECT SUM(customer_ltv) FROM fct_orders", "dependent_columns": ["customer_ltv"]}
    out = _engine(repo).evaluate(bad, role=ROLE, catalog_columns=COLS)
    assert out.status is GovernanceStatus.REJECT
    assert "hallucinated_column" in {f.code for f in out.findings}


def test_undeclared_dependency_is_rejected(repo: Path) -> None:
    bad = {**PAYLOAD, "dependent_columns": ["amount"]}  # SQL also reads status
    out = _engine(repo).evaluate(bad, role=ROLE, catalog_columns=COLS)
    assert out.status is GovernanceStatus.REJECT
    assert "undeclared_column" in {f.code for f in out.findings}


def test_schema_violation_is_rejected_before_validators(repo: Path) -> None:
    out = _engine(repo).evaluate({**PAYLOAD, "aggregation_type": "sum"}, role=ROLE, catalog_columns=COLS)
    assert out.status is GovernanceStatus.REJECT
    assert out.findings[0].validator == "schema"
    assert [v.validator for v in out.verdicts] == ["schema"], "nothing else runs on a shapeless payload"


def test_malformed_json_is_rejected_and_recorded(repo: Path) -> None:
    out = _engine(repo).evaluate("{not json", role=ROLE)
    assert out.status is GovernanceStatus.REJECT and out.findings[0].code == "json"
    _audit_is_clean(repo)


def test_secret_is_caught_and_never_reaches_the_ledger(repo: Path) -> None:
    secret = "sk_live_0123456789abcdefXYZ"
    bad = {**PAYLOAD, "rationale": f"api_key = '{secret}'"}
    out = _engine(repo).evaluate(bad, role=ROLE, catalog_columns=COLS)
    assert out.status is GovernanceStatus.REJECT
    assert "generic_secret" in {f.code for f in out.findings}
    chain = (repo / "provenance" / "chain.jsonl").read_text()
    assert secret not in chain, "the rejection record must not carry what it rejected"


def test_mart_pattern_from_the_overlay_applies(repo: Path) -> None:
    _overlay(repo, {"runtime": {"mart_pattern": "^adv_[a-z0-9_]+$"}})
    out = _engine(repo).evaluate(PAYLOAD, role=ROLE, catalog_columns=COLS)
    assert out.status is GovernanceStatus.REJECT and out.findings[0].validator == "schema"


# ------------------------------------------------------------------ gate --

def test_unknown_role_is_denied(repo: Path) -> None:
    out = _engine(repo).evaluate(PAYLOAD, role="rogue-agent", catalog_columns=COLS)
    assert out.status is GovernanceStatus.REJECT and out.gate is not None
    assert out.gate.rule == "aidf:role"
    assert actions(repo)[out.action_id]["decision"].payload["rule"] == "aidf:role"


def test_role_may_not_write_outside_its_globs(repo: Path) -> None:
    out = _engine(repo).evaluate(PAYLOAD, role=ROLE, target="transform/models/marts/fct_orders.sql", catalog_columns=COLS)
    assert out.status is GovernanceStatus.REJECT and out.gate.rule == "aidf:role"


@pytest.mark.parametrize("target", ["../../../provenance/chain.jsonl", "/etc/passwd", "../../gate.yaml"])
def test_escaping_targets_are_denied(repo: Path, target: str) -> None:
    out = _engine(repo).evaluate(PAYLOAD, role=ROLE, target=target, catalog_columns=COLS)
    assert out.status is GovernanceStatus.REJECT
    assert out.gate.rule in ("aidf:path_traversal", "aidf:immutable")


def test_gate_yaml_denylist_wins_over_role(repo: Path) -> None:
    _overlay(repo, {"runtime": {"roles": {ROLE: {"targets": ["**"]}}}})
    out = _engine(repo).evaluate(PAYLOAD, role=ROLE, target="credentials/aws.txt", catalog_columns=COLS)
    assert out.status is GovernanceStatus.REJECT and out.gate.rule.startswith("denylist:")


def test_gate_yaml_generated_artefact_is_denied(repo: Path) -> None:
    _overlay(repo, {"runtime": {"roles": {ROLE: {"targets": ["**"]}}}})
    out = _engine(repo).evaluate(PAYLOAD, role=ROLE, target="governance/dora/matrix.json", catalog_columns=COLS)
    assert out.status is GovernanceStatus.REJECT and "denylist" in out.gate.rule


# ------------------------------------------------------------- ESCALATED --

def test_elevated_target_holds_until_a_person_approves(repo: Path) -> None:
    _overlay(repo, {"runtime": {"elevated": {"paths": ["governance/metrics/fct_orders/**"], "roles": ["lead_risk_officer"]}}})
    eng = _engine(repo)
    held = eng.evaluate(PAYLOAD, role=ROLE, catalog_columns=COLS)
    assert held.status is GovernanceStatus.ESCALATED and not held.written
    st = actions(repo)[held.action_id]
    assert st["decision"].payload["verdict"] == "hold" and st["decision"].payload["rule"] == "human_oversight"
    assert st["execution"].payload["status"] == "blocked"
    _audit_is_clean(repo)

    # Resubmitting without approval holds again; with it, passes.
    assert eng.evaluate(PAYLOAD, role=ROLE, catalog_columns=COLS).status is GovernanceStatus.ESCALATED
    approve(repo, held.action_id, note="reviewed")
    done = eng.evaluate(PAYLOAD, role=ROLE, catalog_columns=COLS, approved_action_id=held.action_id)
    assert done.status is GovernanceStatus.PASS and done.written
    assert done.gate.rule == "human_oversight"


def test_elevated_role_is_not_held(repo: Path) -> None:
    _overlay(repo, {"runtime": {"elevated": {"paths": ["governance/metrics/**"], "roles": ["lead_risk_officer"]},
                                "roles": {"lead_risk_officer": {"targets": ["governance/metrics/**"]}}}})
    out = _engine(repo).evaluate(PAYLOAD, role="lead_risk_officer", catalog_columns=COLS)
    assert out.status is GovernanceStatus.PASS


# ---------------------------------------------------------------- breaker --

def test_breaker_trips_after_consecutive_rejections(repo: Path) -> None:
    _overlay(repo, {"runtime": {"budgets": {"max_consecutive_validation_failures": 2}}})
    eng = _engine(repo)
    bad = {**PAYLOAD, "sql_definition": "SELECT * FROM fct_orders"}
    assert eng.evaluate(bad, role=ROLE, catalog_columns=COLS).status is GovernanceStatus.REJECT
    assert eng.evaluate(bad, role=ROLE, catalog_columns=COLS).status is GovernanceStatus.REJECT
    assert eng.breaker.state().open
    # Even a good payload is refused while the circuit is open, and the
    # refusal is itself recorded — and does not count as a failure.
    broken = eng.evaluate(PAYLOAD, role=ROLE, catalog_columns=COLS)
    assert broken.status is GovernanceStatus.CIRCUIT_BROKEN and not broken.written
    st = actions(repo)[broken.action_id]
    assert st["decision"].payload["rule"] == "aidf:circuit_breaker" and st["execution"].payload["status"] == "blocked"
    assert eng.breaker.state().consecutive_failures == 2, "consulting the breaker must not move the count"
    _audit_is_clean(repo)


def test_breaker_state_survives_a_new_engine(repo: Path) -> None:
    """The count is in the chain, not in memory: a restart cannot forget it."""
    _overlay(repo, {"runtime": {"budgets": {"max_consecutive_validation_failures": 1}}})
    bad = {**PAYLOAD, "sql_definition": "SELECT * FROM fct_orders"}
    _engine(repo).evaluate(bad, role=ROLE, catalog_columns=COLS)
    assert _engine(repo).breaker.state().open
    assert (repo / "provenance" / "chain.jsonl").exists()
    assert not any(p.name.startswith("breaker") for p in repo.rglob("*.json")), "no side file holds the count"


def test_breaker_reset_needs_a_reason_and_is_recorded(repo: Path) -> None:
    _overlay(repo, {"runtime": {"budgets": {"max_consecutive_validation_failures": 1}}})
    eng = _engine(repo)
    eng.evaluate({**PAYLOAD, "sql_definition": "SELECT * FROM t"}, role=ROLE, catalog_columns=COLS)
    assert eng.breaker.state().open
    with pytest.raises(ValueError):
        eng.breaker.reset("")
    aid = eng.breaker.reset("false positive on a fixture mart")
    assert not eng.breaker.state().open
    st = actions(repo)[aid]
    assert st["execution"].payload["status"] == "ok" and "false positive" in st["execution"].payload["detail"]
    assert eng.evaluate(PAYLOAD, role=ROLE, catalog_columns=COLS).status is GovernanceStatus.PASS
    _audit_is_clean(repo)


def test_a_pass_closes_the_count(repo: Path) -> None:
    _overlay(repo, {"runtime": {"budgets": {"max_consecutive_validation_failures": 3}}})
    eng = _engine(repo)
    bad = {**PAYLOAD, "sql_definition": "SELECT * FROM t"}
    eng.evaluate(bad, role=ROLE, catalog_columns=COLS)
    eng.evaluate(bad, role=ROLE, catalog_columns=COLS)
    eng.evaluate(PAYLOAD, role=ROLE, catalog_columns=COLS)
    assert eng.breaker.state().consecutive_failures == 0


def test_breaker_is_per_entity(repo: Path) -> None:
    (repo / "groups" / "g" / "projects" / "q" / "governance").mkdir(parents=True)
    _overlay(repo, {"runtime": {"budgets": {"max_consecutive_validation_failures": 1}}})
    _engine(repo).evaluate({**PAYLOAD, "sql_definition": "SELECT * FROM t"}, role=ROLE, catalog_columns=COLS)
    assert _engine(repo).breaker.state().open
    assert not GovernanceEngine(repo, "g", "q").breaker.state().open


def test_iteration_budget_is_per_invocation(repo: Path) -> None:
    _overlay(repo, {"runtime": {"budgets": {"max_iterations_per_invocation": 2}}})
    eng = _engine(repo)
    eng.evaluate(PAYLOAD, role=ROLE, catalog_columns=COLS, write=False)
    eng.evaluate(PAYLOAD, role=ROLE, catalog_columns=COLS, write=False)
    with pytest.raises(BudgetExceeded):
        eng.evaluate(PAYLOAD, role=ROLE, catalog_columns=COLS, write=False)
    assert _engine(repo).evaluate(PAYLOAD, role=ROLE, catalog_columns=COLS, write=False).ok


# --------------------------------------------------------------- catalog --

def test_catalogue_comes_from_the_knowledge_graph(repo: Path) -> None:
    """With no explicit columns the engine reads the entity's kg/graph.json;
    a column the graph lacks is a hallucination."""
    kg = repo / "groups" / "g" / "projects" / "p" / "kg"
    kg.mkdir()
    kg.joinpath("graph.json").write_text(json.dumps({
        "nodes": [
            {"id": "model.fct_orders", "kind": "Model", "name": "fct_orders", "layer": "marts", "label": "", "props": {}},
            {"id": "col.fct_orders.amount", "kind": "Column", "name": "amount", "layer": "", "label": "", "props": {}},
            {"id": "col.fct_orders.status", "kind": "Column", "name": "status", "layer": "", "label": "", "props": {}},
        ],
        "edges": [
            {"src": "model.fct_orders", "dst": "col.fct_orders.amount", "kind": "has_column", "props": {}},
            {"src": "model.fct_orders", "dst": "col.fct_orders.status", "kind": "has_column", "props": {}},
        ],
    }))
    eng = _engine(repo)
    assert eng.evaluate(PAYLOAD, role=ROLE, write=False).ok
    ghost = {**PAYLOAD, "sql_definition": "SELECT SUM(ltv) FROM fct_orders", "dependent_columns": ["ltv"]}
    out = eng.evaluate(ghost, role=ROLE, write=False)
    assert out.status is GovernanceStatus.REJECT and "hallucinated_column" in {f.code for f in out.findings}


def test_semantic_model_contract_runs_through_the_same_engine(repo: Path) -> None:
    sm = {"name": "orders", "mart_name": "fct_orders", "primary_entity": "order_id",
          "measures": [{"name": "revenue", "aggregation": "SUM", "expression": "amount"}],
          "author_agent": "platform_orchestrator"}
    out = _engine(repo).evaluate(sm, role="platform_orchestrator", contract="semantic_model", catalog_columns=COLS)
    assert out.ok and out.target.endswith("governance/semantic/fct_orders/orders.json")
    bad = {**sm, "measures": [{"name": "revenue", "aggregation": "SUM", "expression": "DROP TABLE x"}]}
    assert _engine(repo).evaluate(bad, role="platform_orchestrator", contract="semantic_model").status is GovernanceStatus.REJECT


def test_describe_names_the_layers_and_the_breaker(repo: Path) -> None:
    d = _engine(repo).describe()
    assert d["group"] == "g" and d["validators"] == ["schema", "sql_ast", "pii"]
    assert d["breaker"]["open"] is False and len(d["layers"]) == 1


def test_every_record_names_the_engine_tool(repo: Path) -> None:
    _engine(repo).evaluate(PAYLOAD, role=ROLE, catalog_columns=COLS)
    assert {r.tool for r in read_all(repo)} == {TOOL_METRIC}
