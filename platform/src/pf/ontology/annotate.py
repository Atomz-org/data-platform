"""Attach ontology meaning to dlt resources.

Annotations are applied as dlt `x-` hints (which survive into the exported schema
YAML) *and* recorded in a process-local registry so they can be exported to
`contracts/annotations.yaml` without the knowledge graph needing to import dlt.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

import yaml

from pf.ontology.model import load_ontology

T = TypeVar("T")

X_CLASS = "x-ontology-class"
X_ROLE = "x-role"
X_LINKS = "x-links-to"
X_DESC = "x-business-description"


@dataclass
class Annotation:
    resource: str
    concept: str
    source: str = ""
    roles: dict[str, str] = field(default_factory=dict)
    rename: dict[str, str] = field(default_factory=dict)
    links: dict[str, str] = field(default_factory=dict)
    description: str = ""
    grain: str = ""
    #: ISO 4217 code every money column here is denominated in, when the source
    #: carries no currency column of its own. A constant is still a declaration:
    #: what must never happen is a money amount with no denomination anywhere,
    #: because that is what lets dollars be summed with euros.
    currency: str = ""

    def to_dict(self) -> dict[str, Any]:
        out = {
            "resource": self.resource,
            "concept": self.concept,
            "source": self.source,
            "roles": self.roles,
            "rename": self.rename,
            "links": self.links,
            "description": self.description,
            "grain": self.grain,
        }
        if self.currency:
            out["currency"] = self.currency
        return out


_REGISTRY: dict[str, Annotation] = {}


def annotate(
    *,
    concept: str,
    source: str = "raw",
    roles: dict[str, str] | None = None,
    rename: dict[str, str] | None = None,
    links: dict[str, str] | None = None,
    description: str = "",
    grain: str = "",
    currency: str = "",
) -> Callable[[T], T]:
    """Decorator applying ontology meaning to a dlt resource.

    Args:
        concept: Ontology class the resource instantiates, e.g. "Payment".
        roles: column -> role name, e.g. {"amount": "money_amount"}.
        rename: raw column -> warehouse column name, applied in staging.
        links: foreign-key column -> target ontology class.
        description: One line, written for an agent rather than a human.
        grain: What one row means, e.g. "one payment".
        currency: ISO 4217 code for every money column, when the source carries
            no currency column of its own.
    """
    roles = dict(roles or {})
    rename = dict(rename or {})
    links = dict(links or {})

    def wrap(resource: T) -> T:
        name = getattr(resource, "name", None) or getattr(resource, "__name__", "unknown")
        ann = Annotation(
            resource=name,
            concept=concept,
            source=source,
            roles=roles,
            rename=rename,
            links=links,
            description=description,
            grain=grain,
            currency=currency,
        )
        _REGISTRY[name] = ann

        columns: dict[str, dict[str, Any]] = {}
        for col, role in roles.items():
            columns.setdefault(col, {})[X_ROLE] = role
        for col, target in links.items():
            columns.setdefault(col, {})[X_LINKS] = target

        apply_hints = getattr(resource, "apply_hints", None)
        if callable(apply_hints):  # real dlt resource
            # older/newer dlt signature — annotations still registered
            with suppress(TypeError):
                apply_hints(columns=columns)
            table_meta = getattr(resource, "_hints", None)
            if isinstance(table_meta, dict):
                table_meta.setdefault("x-annotations", {})[X_CLASS] = concept

        resource.__pf_annotation__ = ann
        return resource

    return wrap


def concept_of(resource: Any) -> str | None:
    ann = getattr(resource, "__pf_annotation__", None)
    return ann.concept if ann else None


def roles_of(resource: Any) -> dict[str, str]:
    ann = getattr(resource, "__pf_annotation__", None)
    return dict(ann.roles) if ann else {}


def links_of(resource: Any) -> dict[str, str]:
    ann = getattr(resource, "__pf_annotation__", None)
    return dict(ann.links) if ann else {}


def registry() -> dict[str, Annotation]:
    return dict(_REGISTRY)


def export_annotations(path: str | Path) -> Path:
    """Write every registered annotation to YAML for the knowledge graph."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": load_ontology().version,
        "resources": [a.to_dict() for a in sorted(_REGISTRY.values(), key=lambda a: a.resource)],
    }
    out.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return out


def from_proposal(proposal: Any, source: str = "",
                  currency: str = "") -> list[Annotation]:
    """Annotations implied by the **accepted** axioms of an ontology proposal.

    `pf semantic scan` already establishes everything an annotation needs: which
    table instantiates which class, which column identifies it, what role each
    column plays, and which foreign key points at which other class. Leaving a
    human to retype that into `contracts/annotations.yaml` is not review, it is
    transcription — and on a repository with fifty raw tables it is the step
    where an onboarding quietly stops being done properly.

    Only accepted axioms are read, and that is the governance. An annotation
    asserts that a column plays a role in the shared vocabulary; if the axiom
    behind it was rejected or is still awaiting a name, the assertion has no
    backing and must not appear. Relations are never pre-accepted — their
    placeholder `refers_to` names have to be replaced with business verbs first —
    so `links` starts empty and fills in as they are named and approved, which is
    the correct order rather than a limitation.
    """
    accepted = [a for a in proposal.axioms if a.get("accept")]

    tables: dict[str, str] = {}       # class -> table
    identity: dict[str, str] = {}     # class -> identifying column
    roles: dict[str, dict[str, str]] = {}
    links: dict[str, dict[str, str]] = {}
    rows: dict[str, int] = {}

    for a in accepted:
        kind, subject = a["kind"], a["subject"]
        if kind == "class" and a.get("table"):
            tables[subject] = a["table"]
            if a.get("rows"):
                rows[subject] = int(a["rows"])
            if a.get("identity"):
                identity[subject] = a["identity"]
        elif kind == "identity":
            identity[subject] = a["property"]
        elif kind == "property" and a.get("role"):
            cls, _, col = subject.partition(".")
            if col:
                roles.setdefault(cls, {})[col] = a["role"]
        elif kind == "relation" and a.get("via"):
            links.setdefault(a["domain"], {})[a["via"]] = a["range"]

    out: list[Annotation] = []
    for cls, table in sorted(tables.items()):
        col_roles = dict(roles.get(cls, {}))
        key = identity.get(cls)
        if key:
            # The identity is the key whatever the column profiler made of it.
            col_roles[key] = "natural_key"
        # Only where it is needed. Stamping a currency on a resource with no
        # money column asserts a denomination for nothing, and the next reader
        # has to work out whether it means something.
        needs = (any(r == "money_amount" for r in col_roles.values())
                 and not any(r == "currency_code" for r in col_roles.values()))
        out.append(Annotation(
            resource=table,
            concept=cls,
            source=source or proposal.source,
            roles=col_roles,
            links=links.get(cls, {}),
            description=f"Induced from {table} by `pf semantic scan`.",
            grain=f"one {cls.lower()}" + (f" ({rows[cls]:,} rows scanned)"
                                          if cls in rows else ""),
            currency=currency if needs else "",
        ))
    return out


def merge_annotations(path: str | Path, incoming: list[Annotation]) -> tuple[int, int]:
    """Write annotations, never overwriting one that is already there.

    An existing entry is a decision someone made — a business description, a
    grain in real words, a link named after the verb it means. Regenerating over
    the top of that would make `pf semantic annotate` unsafe to re-run, and a
    generator you cannot re-run is one people stop running.
    """
    out = Path(path)
    existing = {a.resource: a for a in load_annotations(out)}
    unmodelled = load_unmodelled(out)
    added = [a for a in incoming if a.resource not in existing]
    merged = sorted([*existing.values(), *added], key=lambda a: a.resource)
    payload: dict[str, Any] = {
        "version": load_ontology().version,
        "resources": [a.to_dict() for a in merged],
    }
    if unmodelled:
        payload["unmodelled"] = unmodelled
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return len(added), len(existing)


def load_unmodelled(path: str | Path) -> dict[str, str]:
    """Raw resources deliberately left without a concept, and why.

    Not every table is an entity. A junction table between two entities is a
    *relation* — annotating it as a class invents something the business does not
    have, and the invented class then appears in the graph, the MDL manifest and
    every agent's vocabulary. Staging tables of pure technical exhaust are the
    same.

    The alternative to recording these is worse than it looks. A conformance rule
    that demands a concept for every table gets satisfied by whatever concept
    makes it stop complaining, and nobody can later tell a considered omission
    from a forgotten one. A reason string is the whole mechanism: it costs a line
    and it converts "we forgot" into "we decided".
    """
    p = Path(path)
    if not p.exists():
        return {}
    payload = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {str(k): str(v) for k, v in (payload.get("unmodelled") or {}).items()
            if str(v).strip()}


def load_annotations(path: str | Path) -> list[Annotation]:
    """Read annotations back from YAML (used by the KG builder and the UI)."""
    p = Path(path)
    if not p.exists():
        return []
    payload = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return [
        Annotation(
            resource=r["resource"],
            concept=r["concept"],
            source=r.get("source", "raw"),
            roles=r.get("roles") or {},
            rename=r.get("rename") or {},
            links=r.get("links") or {},
            description=r.get("description", ""),
            grain=r.get("grain", ""),
            currency=r.get("currency", ""),
        )
        for r in payload.get("resources", [])
    ]
