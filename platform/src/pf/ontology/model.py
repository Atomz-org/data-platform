"""Load and query the platform ontology."""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ONTOLOGY_DIR = Path(__file__).parent


@dataclass(frozen=True)
class OntologyClass:
    name: str
    description: str = ""
    parent: str | None = None
    abstract: bool = False


@dataclass(frozen=True)
class Role:
    name: str
    description: str = ""
    pii: bool = False


@dataclass(frozen=True)
class TopologyEdge:
    src: str
    dst: str
    type: str
    cardinality: str


@dataclass
class Ontology:
    version: int
    classes: dict[str, OntologyClass] = field(default_factory=dict)
    roles: dict[str, Role] = field(default_factory=dict)
    edges: list[TopologyEdge] = field(default_factory=list)

    # -- lookups -------------------------------------------------------------
    def has_class(self, name: str) -> bool:
        return name in self.classes

    def has_role(self, name: str) -> bool:
        return name in self.roles

    def ancestors(self, name: str) -> list[str]:
        """Class names from `name` up to the root, exclusive of `name`."""
        out: list[str] = []
        node = self.classes.get(name)
        while node is not None and node.parent:
            out.append(node.parent)
            node = self.classes.get(node.parent)
        return out

    def is_a(self, name: str, ancestor: str) -> bool:
        return name == ancestor or ancestor in self.ancestors(name)

    def concrete_classes(self) -> list[str]:
        return sorted(n for n, c in self.classes.items() if not c.abstract)

    def pii_roles(self) -> set[str]:
        return {n for n, r in self.roles.items() if r.pii}

    def edge_allowed(self, src: str, dst: str) -> bool:
        """True if a link src -> dst is legal, honouring class inheritance."""
        for e in self.edges:
            if self.is_a(src, e.src) and self.is_a(dst, e.dst):
                return True
            # links are declared on the child side too; accept the inverse
            if self.is_a(src, e.dst) and self.is_a(dst, e.src):
                return True
        return False

    def edges_for(self, name: str) -> list[TopologyEdge]:
        return [e for e in self.edges if self.is_a(name, e.src) or self.is_a(name, e.dst)]


@functools.lru_cache(maxsize=4)
def load_ontology(directory: str | Path | None = None) -> Ontology:
    """Load concepts.yaml + topology.yaml. Cached; pass a directory to override."""
    base = Path(directory) if directory else ONTOLOGY_DIR
    concepts = yaml.safe_load((base / "concepts.yaml").read_text())
    topology = yaml.safe_load((base / "topology.yaml").read_text())

    classes = {
        name: OntologyClass(
            name=name,
            description=(spec or {}).get("description", ""),
            parent=(spec or {}).get("parent"),
            abstract=bool((spec or {}).get("abstract", False)),
        )
        for name, spec in (concepts.get("classes") or {}).items()
    }
    roles = {
        name: Role(
            name=name,
            description=(spec or {}).get("description", ""),
            pii=bool((spec or {}).get("pii", False)),
        )
        for name, spec in (concepts.get("roles") or {}).items()
    }
    edges = [
        TopologyEdge(src=e["from"], dst=e["to"], type=e["type"], cardinality=e["cardinality"])
        for e in (topology.get("edges") or [])
    ]
    return Ontology(version=int(concepts.get("version", 1)), classes=classes, roles=roles, edges=edges)
