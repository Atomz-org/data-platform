"""Load and query the platform ontology, topology and policy.

Three files, three jobs:

  concepts.yaml  what things ARE      classes, identity, datatype properties
  topology.yaml  how they RELATE      named relations, domain/range, cardinality
  policy.yaml    what must HOLD       intent -> constraint -> artifact -> evidence

Keeping them separate matters: the ontology is stable, the topology changes when
a new relation is discovered, and policy changes when governance does. Merging
them would make every policy edit a vocabulary edit.
"""

from __future__ import annotations

import fnmatch
import functools
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

ONTOLOGY_DIR = Path(__file__).parent

# MDL's enum, used verbatim so no translation step can flip a direction.
Cardinality = Literal["ONE_TO_ONE", "ONE_TO_MANY", "MANY_TO_ONE", "MANY_TO_MANY"]

INVERSE_CARDINALITY: dict[str, str] = {
    "ONE_TO_ONE": "ONE_TO_ONE",
    "ONE_TO_MANY": "MANY_TO_ONE",
    "MANY_TO_ONE": "ONE_TO_MANY",
    "MANY_TO_MANY": "MANY_TO_MANY",
}

# Ontology datatype -> MDL column type. MDL types are warehouse-neutral.
MDL_TYPES = {
    "string": "VARCHAR",
    "integer": "BIGINT",
    "decimal": "DECIMAL",
    "float": "DOUBLE",
    "boolean": "BOOLEAN",
    "timestamp": "TIMESTAMP",
    "date": "DATE",
}

# Ontology datatype -> XSD, for the OWL projection.
XSD_TYPES = {
    "string": "xsd:string",
    "integer": "xsd:integer",
    "decimal": "xsd:decimal",
    "float": "xsd:double",
    "boolean": "xsd:boolean",
    "timestamp": "xsd:dateTime",
    "date": "xsd:date",
}


@dataclass(frozen=True)
class Property:
    """A datatype property on a class (OWL DatatypeProperty)."""

    name: str
    datatype: str = "string"
    role: str = ""
    required: bool = False

    @property
    def mdl_type(self) -> str:
        return MDL_TYPES.get(self.datatype, "VARCHAR")

    @property
    def xsd_type(self) -> str:
        return XSD_TYPES.get(self.datatype, "xsd:string")


@dataclass(frozen=True)
class OntologyClass:
    name: str
    label: str = ""
    description: str = ""
    parent: str | None = None
    abstract: bool = False
    identity: str | None = None
    properties: dict[str, Property] = field(default_factory=dict)


# What a review tool should do with a column carrying this role. Deliberately
# tool-agnostic: the ontology declares the *question worth asking*, and each tool
# translates it into whatever check it happens to implement. Recce turns
# `distribution` into a profile diff; a different tool may turn it into an
# anomaly monitor. Neither vocabulary leaks into the other.
#
#   identity      this column identifies a row — align rows on it before comparing
#   distribution  a magnitude; watch for the shape moving
#   categories    a bounded value set; watch for members gained or lost
#   none          do not compare values for this role
REVIEW_INTENTS = frozenset({"identity", "distribution", "categories", "none"})

# Defaults inferred from the declared datatype, so a role added tomorrow is
# reviewed without anyone remembering to wire it up. Only magnitudes get a
# default: whether a string is a bounded category or free text is not knowable
# from `datatype: string`, and guessing wrong makes every review noisy.
_REVIEW_BY_DATATYPE: dict[str, str] = {
    "decimal": "distribution",
    "integer": "distribution",
    "float": "distribution",
    "number": "distribution",
}


@dataclass(frozen=True)
class Role:
    name: str
    datatype: str = "string"
    description: str = ""
    pii: bool = False
    #: Explicit review intent. Empty means "infer from datatype".
    review: str = ""

    @property
    def review_intent(self) -> str:
        """What a review tool should ask of this column.

        PII wins over everything, including an explicit declaration. A value-level
        diff materialises the compared rows into the tool's state file, which is
        a durable, shareable artefact — so diffing an email column writes real
        addresses into something that gets committed and passed around. The
        `pii-not-in-consumption` policy already says PII must not reach the
        consumption layer; this is the same rule applied to review artefacts,
        enforced here so no individual tool has to remember it.
        """
        if self.pii:
            return "none"
        if self.review:
            return self.review
        return _REVIEW_BY_DATATYPE.get(self.datatype, "none")


@dataclass(frozen=True)
class Relation:
    """A named object property. Directional: domain -> range."""

    name: str
    domain: str
    range: str
    cardinality: str
    label: str = ""
    inverse: str = ""
    description: str = ""

    @property
    def inverse_cardinality(self) -> str:
        return INVERSE_CARDINALITY[self.cardinality]

    def describe(self, reverse: bool = False) -> str:
        if reverse:
            return f"{self.range} {self.inverse or 'related to'} {self.domain}"
        return f"{self.domain} {self.label or 'relates to'} {self.range}"


@dataclass(frozen=True)
class Policy:
    id: str
    intent: str
    constraint: str
    severity: str = "error"
    applies_to: dict[str, Any] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    enforced_by: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    @property
    def enforced(self) -> bool:
        return bool(self.enforced_by)


@dataclass
class Ontology:
    version: int
    namespace: str = ""
    prefix: str = "pf"
    classes: dict[str, OntologyClass] = field(default_factory=dict)
    roles: dict[str, Role] = field(default_factory=dict)
    relations: list[Relation] = field(default_factory=list)
    policies: list[Policy] = field(default_factory=list)
    evidence_kinds: list[dict[str, Any]] = field(default_factory=list)

    # -- class lookups -------------------------------------------------------
    def has_class(self, name: str) -> bool:
        return name in self.classes

    def has_role(self, name: str) -> bool:
        return name in self.roles

    def ancestors(self, name: str) -> list[str]:
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

    def has_currency(self, code: str) -> bool:
        """Whether a string is a plausible ISO 4217 code.

        Shape rather than a list. Enumerating all 180 codes here would mean the
        ontology owns a table that changes for reasons that have nothing to do
        with this platform, and rejecting a real currency because the list is a
        year old is worse than accepting a typo — the typo shows up as an empty
        join on the Currency dimension, which is visible.
        """
        return len(code) == 3 and code.isalpha() and code.isupper()

    def identity_of(self, name: str) -> str | None:
        """Identity property, inherited from the nearest ancestor that has one."""
        for cls in [name, *self.ancestors(name)]:
            c = self.classes.get(cls)
            if c and c.identity:
                return c.identity
        return None

    def properties_of(self, name: str) -> dict[str, Property]:
        """Own properties merged over inherited ones."""
        merged: dict[str, Property] = {}
        for cls in reversed([name, *self.ancestors(name)]):
            c = self.classes.get(cls)
            if c:
                merged.update(c.properties)
        return merged

    # -- topology ------------------------------------------------------------
    def relation(self, name: str) -> Relation | None:
        return next((r for r in self.relations if r.name == name), None)

    def relations_for(self, cls: str) -> list[Relation]:
        return [r for r in self.relations
                if self.is_a(cls, r.domain) or self.is_a(cls, r.range)]

    def find_relation(self, src: str, dst: str) -> Relation | None:
        """The relation connecting two classes, in either direction."""
        for r in self.relations:
            if self.is_a(src, r.domain) and self.is_a(dst, r.range):
                return r
            if self.is_a(src, r.range) and self.is_a(dst, r.domain):
                return r
        return None

    def edge_allowed(self, src: str, dst: str) -> bool:
        """True if a link src -> dst is declared in the topology."""
        return self.find_relation(src, dst) is not None

    # Retained for callers written against v1.
    def edges_for(self, name: str) -> list[Relation]:
        return self.relations_for(name)

    # -- policy --------------------------------------------------------------
    def policy(self, pid: str) -> Policy | None:
        return next((p for p in self.policies if p.id == pid), None)

    def policies_for_role(self, role: str) -> list[Policy]:
        out = []
        for p in self.policies:
            target = p.applies_to
            if target.get("role") == role or ("role_glob" in target and fnmatch.fnmatch(role, target["role_glob"])):
                out.append(p)
        return out

    def unenforced_policies(self) -> list[Policy]:
        return [p for p in self.policies if not p.enforced]


def _parse_properties(spec: dict[str, Any]) -> dict[str, Property]:
    out: dict[str, Property] = {}
    for pname, pspec in (spec.get("properties") or {}).items():
        pspec = pspec or {}
        out[pname] = Property(
            name=pname,
            datatype=pspec.get("datatype", "string"),
            role=pspec.get("role", ""),
            required=bool(pspec.get("required", False)),
        )
    return out


@functools.lru_cache(maxsize=4)
def load_ontology(directory: str | Path | None = None) -> Ontology:
    """Load concepts + topology + policy. Cached; pass a directory to override."""
    base = Path(directory) if directory else ONTOLOGY_DIR
    concepts = yaml.safe_load((base / "concepts.yaml").read_text()) or {}
    topology = yaml.safe_load((base / "topology.yaml").read_text()) or {}
    policy_path = base / "policy.yaml"
    policy_doc = yaml.safe_load(policy_path.read_text()) if policy_path.exists() else {}

    classes = {
        name: OntologyClass(
            name=name,
            label=(spec or {}).get("label", name),
            description=(spec or {}).get("description", ""),
            parent=(spec or {}).get("parent"),
            abstract=bool((spec or {}).get("abstract", False)),
            identity=(spec or {}).get("identity"),
            properties=_parse_properties(spec or {}),
        )
        for name, spec in (concepts.get("classes") or {}).items()
    }

    roles = {
        name: Role(
            name=name,
            datatype=(spec or {}).get("datatype", "string"),
            description=(spec or {}).get("description", ""),
            pii=bool((spec or {}).get("pii", False)),
            review=(spec or {}).get("review", ""),
        )
        for name, spec in (concepts.get("roles") or {}).items()
    }

    relations = [
        Relation(
            name=r["name"], domain=r["domain"], range=r["range"],
            cardinality=r["cardinality"], label=r.get("label", ""),
            inverse=r.get("inverse", ""), description=r.get("description", ""),
        )
        for r in (topology.get("relations") or [])
    ]

    policies = [
        Policy(
            id=p["id"], intent=p.get("intent", "").strip(),
            constraint=p.get("constraint", ""), severity=p.get("severity", "error"),
            applies_to=p.get("applies_to") or {}, params=p.get("params") or {},
            enforced_by=p.get("enforced_by") or [], evidence=p.get("evidence") or [],
        )
        for p in (policy_doc.get("policies") or [])
    ]

    return Ontology(
        version=int(concepts.get("version", 1)),
        namespace=concepts.get("namespace", ""),
        prefix=concepts.get("prefix", "pf"),
        classes=classes, roles=roles, relations=relations,
        policies=policies,
        evidence_kinds=policy_doc.get("evidence_kinds") or [],
    )


def load_group_ontology(root: str | Path, group: str) -> Ontology:
    """Platform ontology with a group's extension merged over it.

    Three layers, and the separation is what keeps companies independent:

        platform   universal vocabulary — stable, shared, rarely changes
        group      this family's own classes and relations — extension.yaml
        project    physical bindings — contracts/annotations.yaml

    A class a single company invented does not belong in the platform ontology;
    putting it there makes every other company inherit a term that means nothing
    to them. The extension is where induced, steward-approved additions land, and
    promoting one to the platform is a separate, deliberate act.
    """
    base = load_ontology()
    ext_path = Path(root) / "groups" / group / "ontology" / "extension.yaml"
    if not ext_path.exists():
        return base

    ext = yaml.safe_load(ext_path.read_text()) or {}

    classes = dict(base.classes)
    for name, spec in (ext.get("classes") or {}).items():
        spec = spec or {}
        existing = classes.get(name)
        # A group may add properties to a platform class without redefining it.
        props = dict(existing.properties) if existing else {}
        props.update(_parse_properties(spec))
        classes[name] = OntologyClass(
            name=name,
            label=spec.get("label", existing.label if existing else name),
            description=spec.get("description", existing.description if existing else ""),
            parent=spec.get("parent", existing.parent if existing else None),
            abstract=bool(spec.get("abstract", existing.abstract if existing else False)),
            identity=spec.get("identity", existing.identity if existing else None),
            properties=props,
        )

    roles = dict(base.roles)
    for name, spec in (ext.get("roles") or {}).items():
        spec = spec or {}
        roles[name] = Role(name=name, datatype=spec.get("datatype", "string"),
                           description=spec.get("description", ""),
                           pii=bool(spec.get("pii", False)),
                           review=spec.get("review", ""))

    relations = list(base.relations)
    by_name = {r.name for r in relations}
    for r in (ext.get("relations") or []):
        if r["name"] in by_name:
            relations = [x for x in relations if x.name != r["name"]]
        relations.append(Relation(
            name=r["name"], domain=r["domain"], range=r["range"],
            cardinality=r["cardinality"], label=r.get("label", ""),
            inverse=r.get("inverse", ""), description=r.get("description", "")))

    return Ontology(version=base.version, namespace=base.namespace, prefix=base.prefix,
                    classes=classes, roles=roles, relations=relations,
                    policies=base.policies, evidence_kinds=base.evidence_kinds)


# v1 compatibility: callers importing TopologyEdge get the Relation type.
TopologyEdge = Relation
