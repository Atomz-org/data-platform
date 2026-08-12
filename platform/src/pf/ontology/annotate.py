"""Attach ontology meaning to dlt resources.

Annotations are applied as dlt `x-` hints (which survive into the exported schema
YAML) *and* recorded in a process-local registry so they can be exported to
`contracts/annotations.yaml` without the knowledge graph needing to import dlt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, TypeVar

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource": self.resource,
            "concept": self.concept,
            "source": self.source,
            "roles": self.roles,
            "rename": self.rename,
            "links": self.links,
            "description": self.description,
            "grain": self.grain,
        }


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
) -> Callable[[T], T]:
    """Decorator applying ontology meaning to a dlt resource.

    Args:
        concept: Ontology class the resource instantiates, e.g. "Payment".
        roles: column -> role name, e.g. {"amount": "money_amount"}.
        rename: raw column -> warehouse column name, applied in staging.
        links: foreign-key column -> target ontology class.
        description: One line, written for an agent rather than a human.
        grain: What one row means, e.g. "one payment".
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
        )
        _REGISTRY[name] = ann

        columns: dict[str, dict[str, Any]] = {}
        for col, role in roles.items():
            columns.setdefault(col, {})[X_ROLE] = role
        for col, target in links.items():
            columns.setdefault(col, {})[X_LINKS] = target

        apply_hints = getattr(resource, "apply_hints", None)
        if callable(apply_hints):  # real dlt resource
            try:
                apply_hints(columns=columns)
            except TypeError:  # older/newer dlt signature — annotations still registered
                pass
            table_meta = getattr(resource, "_hints", None)
            if isinstance(table_meta, dict):
                table_meta.setdefault("x-annotations", {})[X_CLASS] = concept

        setattr(resource, "__pf_annotation__", ann)
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
    out.write_text(yaml.safe_dump(payload, sort_keys=False))
    return out


def load_annotations(path: str | Path) -> list[Annotation]:
    """Read annotations back from YAML (used by the KG builder and the UI)."""
    p = Path(path)
    if not p.exists():
        return []
    payload = yaml.safe_load(p.read_text()) or {}
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
        )
        for r in payload.get("resources", [])
    ]
