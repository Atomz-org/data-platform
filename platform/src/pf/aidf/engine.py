"""The governance engine: gate, contract, validators, ledger — in that order,
and never a different one.

    evaluate(payload, target, role)
      1. budget      one more iteration within this invocation
      2. breaker     is the circuit open for this entity?  -> CIRCUIT_BROKEN
      3. gate        may this role write this path?         -> REJECT / ESCALATED
      4. contract    does the payload satisfy the schema?   -> REJECT
      5. validators  SQL AST, PII, catalogue                -> REJECT
      6. ledger      INTENT -> DECISION -> EXECUTION, hash-linked
      7. write       the validated, canonical record, only after 6

Every branch reaches the ledger. A rejection is recorded as a `deny` DECISION
paired with a `blocked` EXECUTION, which is the pairing `pf provenance verify`
checks — a rejection that executed anyway would fail the audit, and so would a
rejection that was never written. What is recorded about the payload is its
SHA-256 and the findings, never the payload: the PII finding must not put the
e-mail address it caught into a file every auditor reads.

The engine is built from an entity — `(root, group, project)` — and nothing
else. Its rules come from the entity's resolved `aidf.yaml`, its catalogue from
the entity's knowledge graph, its ledger from the repository's one chain. There
is no per-company code path here and nothing to add when the next project is
scaffolded.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from pf.aidf import catalog as catalog_mod
from pf.aidf.breaker import TOOL_METRIC, BudgetExceeded, CircuitBreaker
from pf.aidf.config import AidfConfig, load
from pf.aidf.gate import ActionGate, ActionGatePolicyViolation, GateDecision
from pf.aidf.schemas import (
    CONTRACTS,
    GovernanceStatus,
    MartMetricContract,
    SemanticModelContract,
    validate_payload,
)
from pf.aidf.validators import Finding, PiiScrubber, SqlAstValidator, Verdict
from pf.provenance import decision, execution, head, intent, is_approved, new_action_id

__all__ = ["ActionGatePolicyViolation", "BudgetExceeded", "GovernanceEngine", "Outcome"]


@dataclass
class Outcome:
    status: GovernanceStatus
    action_id: str
    target: str  # repo-relative
    role: str
    contract: str
    gate: GateDecision | None = None
    payload: dict[str, Any] | None = None  # the validated, canonical record
    findings: list[Finding] = field(default_factory=list)
    verdicts: list[Verdict] = field(default_factory=list)
    written: bool = False
    chain_seq: int = -1
    chain_hash: str = ""
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is GovernanceStatus.PASS

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "ok": self.ok,
            "action_id": self.action_id,
            "target": self.target,
            "role": self.role,
            "contract": self.contract,
            "gate": None if self.gate is None else {"verdict": self.gate.verdict, "rule": self.gate.rule,
                                                    "message": self.gate.message},
            "findings": [f.to_dict() for f in self.findings],
            "verdicts": [v.to_dict() for v in self.verdicts],
            "written": self.written,
            "chain": {"seq": self.chain_seq, "hash": self.chain_hash},
            "message": self.message,
            "payload": self.payload,
        }


def _sha256(obj: Any) -> str:
    if isinstance(obj, (bytes, bytearray)):
        return hashlib.sha256(obj).hexdigest()
    if isinstance(obj, str):
        return hashlib.sha256(obj.encode("utf-8")).hexdigest()
    body = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


class GovernanceEngine:
    def __init__(self, root: Path, group: str, project: str, *, config: AidfConfig | None = None) -> None:
        self.root = Path(root)
        self.group = group
        self.project = project
        self.project_dir = self.root / "groups" / group / "projects" / project
        self.config = config or load(self.root, group, project)
        self.gate = ActionGate(self.root, group, project, self.config)
        self.breaker = CircuitBreaker(self.root, group, project, self.config.budgets)

    # -- helpers --------------------------------------------------------------
    @staticmethod
    def default_target(contract: str, payload: dict[str, Any]) -> str:
        """Where a validated record lands when the caller does not say."""
        mart = str(payload.get("mart_name") or "unknown")
        if contract == "semantic_model":
            return f"governance/semantic/{mart}/{payload.get('name', 'model')}.json"
        return f"governance/metrics/{mart}/{payload.get('metric_name', 'metric')}.json"

    def describe(self) -> dict[str, Any]:
        """What this entity is governed by. For `pf govern check` and the UI."""
        return {
            "group": self.group, "project": self.project,
            "layers": list(self.config.layers),
            "dialect": self.config.dialect,
            "mart_pattern": self.config.mart_pattern,
            "validators": list(self.config.validators),
            "roles": self.config.roles,
            "elevated": {"paths": self.config.elevated_paths, "roles": self.config.elevated_roles},
            "budgets": self.config.budgets,
            "breaker": self.breaker.state().to_dict(),
        }

    # -- the evaluation --------------------------------------------------------
    def evaluate(
        self,
        payload: str | dict[str, Any],
        *,
        role: str,
        target: str = "",
        contract: str = "mart_metric",
        catalog_columns: set[str] | None = None,
        write: bool = True,
        approved_action_id: str = "",
    ) -> Outcome:
        if contract not in CONTRACTS:
            raise ValueError(f"unknown contract {contract!r}; one of {sorted(CONTRACTS)}")
        self.breaker.note_iteration()

        # Parse first, so the target can be derived, but judge nothing yet.
        raw: dict[str, Any] | None
        parse_error = ""
        if isinstance(payload, str):
            try:
                loaded = json.loads(payload)
                raw = loaded if isinstance(loaded, dict) else None
                if raw is None:
                    parse_error = "payload must be a JSON object"
            except json.JSONDecodeError as exc:
                raw, parse_error = None, f"malformed JSON: {exc.msg} at {exc.pos}"
        else:
            raw = dict(payload)
        target = target or self.default_target(contract, raw or {})
        payload_sha = _sha256(payload if isinstance(payload, str) else raw)
        summary = f"{contract} via {role} -> {target}"

        # 2. breaker
        allowed, why = self.breaker.check()
        if not allowed:
            return self._blocked(GovernanceStatus.CIRCUIT_BROKEN, role, target, contract, summary, payload_sha,
                                 rule="aidf:circuit_breaker", message=why,
                                 findings=[Finding("breaker", "circuit_open", why)])

        # 3. gate
        gd = self.gate.authorize(target, role)
        if gd.verdict == "hold" and approved_action_id and is_approved(self.root, approved_action_id):
            gd = GateDecision("allow", "human_oversight", f"approved as {approved_action_id[:12]}", gd.path)
        if gd.verdict == "deny":
            return self._blocked(GovernanceStatus.REJECT, role, gd.path, contract, summary, payload_sha,
                                 rule=gd.rule, message=gd.message,
                                 findings=[Finding("gate", gd.rule, gd.message)], gate=gd)
        if gd.verdict == "hold":
            return self._blocked(GovernanceStatus.ESCALATED, role, gd.path, contract, summary, payload_sha,
                                 rule=gd.rule, message=gd.message,
                                 findings=[Finding("gate", gd.rule, gd.message, severity="warn")], gate=gd,
                                 verdict="hold")

        # 4. contract
        findings: list[Finding] = []
        verdicts: list[Verdict] = []
        model = None
        if raw is None:
            findings.append(Finding("schema", "json", parse_error or "payload is not a JSON object", path="$"))
        else:
            try:
                model = validate_payload(contract, raw, mart_pattern=self.config.mart_pattern)
            except ValidationError as exc:
                for err in exc.errors():
                    loc = ".".join(str(x) for x in err.get("loc", ())) or "$"
                    findings.append(Finding("schema", str(err.get("type", "invalid")), str(err.get("msg", "")),
                                            path=loc))
        schema_v = Verdict("schema", list(findings), {"contract": contract})
        verdicts.append(schema_v)

        # 5. validators — only over a payload that has a shape
        if model is not None:
            verdicts.extend(self._run_validators(model, raw or {}, catalog_columns))
            findings.extend(f for v in verdicts[1:] for f in v.findings)

        errors = [f for f in findings if f.severity == "error"]
        if errors:
            first = errors[0]
            return self._blocked(GovernanceStatus.REJECT, role, gd.path, contract, summary, payload_sha,
                                 rule=f"aidf:{first.validator}", message=first.message,
                                 findings=findings, verdicts=verdicts, gate=gd)

        # 6 + 7. ledger, then the write
        assert model is not None
        canonical = model.canonical()
        aid = new_action_id()
        intent(self.root, tool=TOOL_METRIC, target=gd.path, summary=summary, group=self.group,
               project=self.project, action_id=aid,
               payload={"role": role, "contract": contract, "payload_sha256": payload_sha})
        decision(self.root, aid, verdict="allow", rule=gd.rule, message=gd.message, tool=TOOL_METRIC,
                 target=gd.path, group=self.group, project=self.project,
                 payload={"validators": [v.validator for v in verdicts],
                          "checked": {v.validator: v.checked for v in verdicts},
                          "warnings": [f.to_dict() for f in findings]})
        written = False
        try:
            if write:
                out = self.project_dir / self.gate.normalise(target)  # type: ignore[arg-type]
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(canonical, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                written = True
        except OSError as exc:
            execution(self.root, aid, status="error", tool=TOOL_METRIC, target=gd.path, group=self.group,
                      project=self.project, detail=f"write failed: {exc}"[:400],
                      payload={"aidf_status": GovernanceStatus.REJECT.value, "role": role})
            raise
        rec = execution(self.root, aid, status="ok", tool=TOOL_METRIC, target=gd.path, group=self.group,
                        project=self.project, detail=f"{contract} written" if written else f"{contract} validated",
                        payload={"aidf_status": GovernanceStatus.PASS.value, "role": role,
                                 "record_sha256": _sha256(canonical), "written": written})
        return Outcome(GovernanceStatus.PASS, aid, gd.path, role, contract, gate=gd, payload=canonical,
                       findings=findings, verdicts=verdicts, written=written,
                       chain_seq=rec.seq, chain_hash=rec.hash, message="validated and recorded")

    # -- validators -----------------------------------------------------------
    def _run_validators(self, model: Any, raw: dict[str, Any], catalog_columns: set[str] | None) -> list[Verdict]:
        out: list[Verdict] = []
        rt = self.config.runtime
        mart = getattr(model, "mart_name", "")
        for name in self.config.validators:
            if name == "schema":
                continue
            if name == "sql_ast":
                cols = catalog_columns
                if cols is None and mart:
                    cols = catalog_mod.columns_for(self.project_dir, mart)
                tables = catalog_mod.tables_for(self.project_dir)
                sqlv = SqlAstValidator(self.config.dialect, allowed_columns=cols, allowed_tables=tables,
                                       system_schemas=rt.get("system_schemas"), allow_star=bool(rt.get("allow_star")))
                if isinstance(model, MartMetricContract):
                    v = sqlv.validate(model.sql_definition, path="sql_definition")
                    if model.filter_expression:
                        fv = sqlv.validate(f"SELECT 1 WHERE {model.filter_expression}", path="filter_expression")
                        v.findings.extend(fv.findings)
                    referenced = sqlv.referenced_columns(model.sql_definition)
                    declared = {c.lower() for c in model.dependent_columns}
                    undeclared = sorted(referenced - declared)
                    if undeclared:
                        v.findings.append(Finding("sql_ast", "undeclared_column",
                                                  f"SQL reads {undeclared} but dependent_columns does not list them",
                                                  path="dependent_columns"))
                    unused = sorted(declared - referenced)
                    if unused and referenced:
                        v.findings.append(Finding("sql_ast", "unused_dependency",
                                                  f"dependent_columns lists {unused} the SQL never reads",
                                                  severity="warn", path="dependent_columns"))
                    if cols is not None:
                        ghost = sorted(declared - cols)
                        if ghost:
                            v.findings.append(Finding("sql_ast", "hallucinated_column",
                                                      f"dependent_columns not in the mart's catalogue: {ghost}",
                                                      path="dependent_columns"))
                elif isinstance(model, SemanticModelContract):
                    v = Verdict("sql_ast", checked={"fragments": 0,
                                                    "catalog": "present" if cols is not None else "absent"})
                    for i, frag in enumerate(model.sql_fragments()):
                        sub = sqlv.validate(frag, path=f"fragment[{i}]")
                        v.findings.extend(sub.findings)
                        v.checked["fragments"] += 1
                else:  # pragma: no cover - CONTRACTS is closed
                    continue
                out.append(v)
            elif name == "pii":
                out.append(PiiScrubber(rt.get("pii", {}).get("allow")).validate_payload(raw))
            else:
                out.append(Verdict(name, [Finding(name, "unknown_validator",
                                                  f"aidf.yaml names validator `{name}`, which does not exist")]))
        return out

    # -- the rejected branches ---------------------------------------------------
    def _blocked(self, status: GovernanceStatus, role: str, target: str, contract: str, summary: str,
                 payload_sha: str, *, rule: str, message: str, findings: list[Finding],
                 verdicts: list[Verdict] | None = None, gate: GateDecision | None = None,
                 verdict: str = "deny") -> Outcome:
        aid = new_action_id()
        intent(self.root, tool=TOOL_METRIC, target=target, summary=summary, group=self.group,
               project=self.project, action_id=aid,
               payload={"role": role, "contract": contract, "payload_sha256": payload_sha})
        decision(self.root, aid, verdict=verdict, rule=rule, message=message[:400], tool=TOOL_METRIC,
                 target=target, group=self.group, project=self.project,
                 payload={"findings": [f.to_dict() for f in findings][:50]})
        rec = execution(self.root, aid, status="blocked", tool=TOOL_METRIC, target=target, group=self.group,
                        project=self.project, detail=f"{status.value}: {message}"[:400],
                        payload={"aidf_status": status.value, "role": role})
        return Outcome(status, aid, target, role, contract, gate=gate, findings=findings,
                       verdicts=verdicts or [], chain_seq=rec.seq, chain_hash=rec.hash, message=message)


def chain_head(root: Path) -> tuple[int, str]:
    h = head(root)
    return h.seq, h.hash
