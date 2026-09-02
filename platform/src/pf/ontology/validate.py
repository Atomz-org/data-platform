"""Conformance checks. Wired into `pf check` and CI.

Rules enforced:
  1. Every annotated resource declares a class that exists and is concrete.
  2. Every role name exists in the ontology.
  3. Every `links` target is a legal edge in the topology.
  4. Every money_amount column has a sibling currency_code on the same resource.
  5. Every resource declares exactly one natural_key or surrogate_key.
  6. A group instance may only select classes the platform ontology defines.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from pf.ontology.annotate import Annotation, load_annotations
from pf.ontology.model import Ontology, load_ontology

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class ValidationIssue:
    severity: Severity
    rule: str
    subject: str
    message: str

    def __str__(self) -> str:
        mark = "ERROR" if self.severity == "error" else "WARN "
        return f"{mark} [{self.rule}] {self.subject}: {self.message}"


def validate_sources(
    annotations: Iterable[Annotation], ontology: Ontology | None = None
) -> list[ValidationIssue]:
    onto = ontology or load_ontology()
    issues: list[ValidationIssue] = []

    for ann in annotations:
        subj = ann.resource

        if not onto.has_class(ann.concept):
            issues.append(
                ValidationIssue("error", "unknown-class", subj,
                                f"concept '{ann.concept}' is not in the ontology")
            )
        elif onto.classes[ann.concept].abstract:
            issues.append(
                ValidationIssue("error", "abstract-class", subj,
                                f"concept '{ann.concept}' is abstract; use a concrete subclass")
            )

        for col, role in ann.roles.items():
            if not onto.has_role(role):
                issues.append(
                    ValidationIssue("error", "unknown-role", f"{subj}.{col}",
                                    f"role '{role}' is not in the ontology")
                )

        for col, target in ann.links.items():
            if not onto.has_class(target):
                issues.append(
                    ValidationIssue("error", "unknown-link-target", f"{subj}.{col}",
                                    f"links-to '{target}' is not in the ontology")
                )
            elif onto.has_class(ann.concept) and not onto.edge_allowed(ann.concept, target):
                issues.append(
                    ValidationIssue("error", "illegal-edge", f"{subj}.{col}",
                                    f"topology has no edge between "
                                    f"'{ann.concept}' and '{target}'")
                )

        # A money column has to say what it is denominated in, but the currency
        # is not always a column. Most single-currency sources simply do not
        # carry one, and the old rule left them with two bad options: annotate a
        # column that does not exist, or drop the `money_amount` role and lose
        # currency normalisation entirely. `currency: USD` on the resource is the
        # third and truthful one — the denomination is still declared, it is just
        # declared as a constant. What stays an error is money with no
        # denomination at all, which is the case that actually silently adds
        # dollars to euros.
        money = [c for c, r in ann.roles.items() if r == "money_amount"]
        has_currency = any(r == "currency_code" for r in ann.roles.values())
        if money and not has_currency and not ann.currency:
            issues.append(
                ValidationIssue("error", "money-without-currency", subj,
                                f"columns {money} are money_amount but this resource "
                                f"annotates no currency_code column and declares no "
                                f"constant `currency:`")
            )
        if ann.currency and not onto.has_currency(ann.currency):
            issues.append(
                ValidationIssue("error", "unknown-currency", subj,
                                f"currency '{ann.currency}' is not a known code")
            )

        keys = [c for c, r in ann.roles.items() if r in ("natural_key", "surrogate_key")]
        if not keys:
            issues.append(
                ValidationIssue("warning", "no-key", subj,
                                "no natural_key or surrogate_key annotated; "
                                "dbt uniqueness tests cannot be generated")
            )
        elif len(keys) > 1:
            issues.append(
                ValidationIssue("warning", "multiple-keys", subj,
                                f"multiple key columns {keys}; compound keys should be "
                                f"declared in the resource primary_key instead")
            )

    return issues


def validate_topology(ontology: Ontology | None = None) -> list[ValidationIssue]:
    """Check the ontology and topology are internally coherent.

    Enforces the policies `entity-requires-identity` and `link-must-be-in-topology`
    at the vocabulary level, before any project depends on them. A class with no
    identity cannot produce a join condition, so every downstream projection of it
    is a guess — that is worth failing on rather than discovering in BI.
    """
    onto = ontology or load_ontology()
    issues: list[ValidationIssue] = []

    for name, cls in onto.classes.items():
        if cls.abstract:
            continue
        if not onto.identity_of(name):
            issues.append(ValidationIssue(
                "error", "class-without-identity", name,
                "no identity property (own or inherited); joins and MDL/OWL "
                "projections cannot be derived"))
        for pname, prop in cls.properties.items():
            if prop.role and not onto.has_role(prop.role):
                issues.append(ValidationIssue(
                    "error", "unknown-role", f"{name}.{pname}",
                    f"role '{prop.role}' is not in the ontology"))

    seen: set[str] = set()
    for rel in onto.relations:
        if rel.name in seen:
            issues.append(ValidationIssue("error", "duplicate-relation", rel.name,
                                          "relation names must be unique"))
        seen.add(rel.name)
        for role_name, cls in (("domain", rel.domain), ("range", rel.range)):
            if not onto.has_class(cls):
                issues.append(ValidationIssue(
                    "error", "unknown-relation-endpoint", rel.name,
                    f"{role_name} '{cls}' is not an ontology class"))
        if not rel.inverse:
            issues.append(ValidationIssue(
                "warning", "relation-without-inverse", rel.name,
                "no inverse name; the relation cannot be described in reverse"))

    for p in onto.policies:
        if not p.enforced_by:
            issues.append(ValidationIssue(
                "warning", "unenforced-policy", p.id,
                "declared with no enforcing artifact — intent without a check"))
        for e in p.evidence:
            if e not in {k["id"] for k in onto.evidence_kinds}:
                issues.append(ValidationIssue(
                    "warning", "unknown-evidence", p.id,
                    f"evidence '{e}' is not a declared evidence kind"))
    return issues


def validate_instance(instance_path: str | Path, ontology: Ontology | None = None) -> list[ValidationIssue]:
    """Validate a group's `ontology/instance.yaml` against the platform ontology."""
    onto = ontology or load_ontology()
    p = Path(instance_path)
    if not p.exists():
        return [ValidationIssue("error", "missing-instance", str(p), "instance.yaml not found")]

    payload = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    issues: list[ValidationIssue] = []
    for cls in payload.get("classes", []) or []:
        if not onto.has_class(cls):
            issues.append(
                ValidationIssue("error", "unknown-class", str(p),
                                f"'{cls}' is not defined in the platform ontology")
            )
    return issues


def _ontology_for(project_dir: Path) -> Ontology:
    """The platform ontology plus this project's group extension.

    Loading only the platform ontology here was a real failure, not a
    simplification: every concept a group had legitimately added through
    `pf semantic approve` came back as "not in the ontology", so a project that
    passed the ladder's own conformance check failed `pf check` and `pf bootstrap`
    on the same annotations. The group is derivable from the path — a project
    lives at `<root>/groups/<group>/projects/<project>` — so there is no reason
    to validate against a vocabulary the project does not actually use.
    """
    from pf.ontology.model import load_group_ontology

    parts = project_dir.resolve().parts
    if "groups" in parts and "projects" in parts:
        i = parts.index("groups")
        root = Path(*parts[:i]) if i else Path("/")
        group = parts[i + 1]
        try:
            return load_group_ontology(root, group)
        except (OSError, ValueError):
            pass
    return load_ontology()


def validate_project(project_dir: str | Path) -> list[ValidationIssue]:
    """Validate one project's exported annotations."""
    pdir = Path(project_dir)
    anns = load_annotations(pdir / "contracts" / "annotations.yaml")
    if not anns:
        return [
            ValidationIssue("warning", "no-annotations", str(project_dir),
                            "contracts/annotations.yaml is missing or empty; "
                            "run `pf seed` or the pipeline to export it")
        ]
    return validate_sources(anns, _ontology_for(pdir))


def pii_columns(annotations: Iterable[Annotation], ontology: Ontology | None = None) -> list[tuple[str, str, str]]:
    """(resource, column, role) for every PII-tagged column."""
    onto = ontology or load_ontology()
    pii = onto.pii_roles()
    return [
        (a.resource, col, role)
        for a in annotations
        for col, role in a.roles.items()
        if role in pii
    ]
