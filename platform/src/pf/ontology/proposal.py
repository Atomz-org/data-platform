"""Ontology proposals: draft → reviewed → approved → applied.

The workflow exists because vocabulary is a shared asset. Induction can suggest
that `accounts` is a `Customer`; only a person can decide it, because the cost of
being wrong is not a broken build — it is two teams meaning different things by
the same word for a year.

    pf ontology scan     <g> <p>        induce a proposal from what actually landed
    pf ontology review   <g> <id>       what it would change, and what it unlocks
    <edit the YAML>                     the proposal is a working document
    pf ontology approve  <g> <id>       merge into the group extension, then rebuild

Design decisions worth stating:

* **The proposal is plain YAML with comments preserved on write.** A steward's
  primary tool is a text editor, not a CLI flag. Every axiom carries its evidence
  inline so a reviewer can disagree with the reasoning, not just the conclusion.
* **`accept: false` is the default for anything below high confidence, and for
  every PII inference regardless of confidence.** Silence must not approve.
* **Approval is recorded**, with who and when, in the proposal itself — the
  applied file is the audit trail for why a term entered the vocabulary.
* **Nothing is deleted.** Approving writes to the group extension; the proposal
  stays as the record.
"""

from __future__ import annotations

import getpass
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml

Status = Literal["draft", "approved", "applied"]

HEADER = """\
# ONTOLOGY PROPOSAL — {status}
#
# Induced from {source} in {group}/{project} on {created}.
# Nothing here is in effect until `pf ontology approve {group} {pid}`.
#
# HOW TO REVIEW
#   * Every axiom carries `evidence` (what was observed) and `rationale` (why the
#     rule fired). Disagree with the reasoning, not just the conclusion.
#   * Set `accept: true` on what you want. Anything left false is dropped.
#   * Edit freely — rename a class, set a `parent`, give a relation its real
#     business verb. Your edits are the point; this file is a draft, not a result.
#   * `refers_to` relation names are placeholders. A relation called
#     `payment_refers_to_customer` tells a reader nothing; `customer_pays_payment`
#     tells them everything.
#
# WHAT APPROVAL DOES
#   Merges accepted axioms into groups/{group}/ontology/extension.yaml, then
#   rebuilds the knowledge graph, the MDL manifest and the reporting layer for
#   every project in this group. The platform ontology is NOT modified — promoting
#   a term to the platform is a separate, deliberate act.
"""


@dataclass
class Proposal:
    pid: str
    group: str
    project: str
    source: str
    created: str
    status: Status
    axioms: list[dict[str, Any]]
    approved_by: str = ""
    approved_at: str = ""

    @property
    def accepted(self) -> list[dict[str, Any]]:
        return [a for a in self.axioms if a.get("accept")]

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for a in self.axioms:
            out[a["kind"]] = out.get(a["kind"], 0) + 1
        return out


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def proposals_dir(root: Path, group: str) -> Path:
    return Path(root) / "groups" / group / "ontology" / "proposals"


def _default_accept(axiom: dict[str, Any]) -> bool:
    """What may be pre-accepted.

    High-confidence structural facts only. PII is never pre-accepted at any
    confidence: a tag that arrives without a human saying yes carries authority
    it did not earn, and the mart policy will then enforce it.
    """
    if str(axiom.get("role", "")).startswith("pii_"):
        return False
    if axiom["kind"] == "relation":
        return False          # a placeholder name must be renamed before it lands
    return axiom.get("confidence") == "high"


def create(root: Path, group: str, project: str, source: str,
           axioms: list[Any]) -> Proposal:
    created = _now()
    pid = f"{created[:10]}-{source}"
    payload = []
    for a in axioms:
        d = a.to_dict() if hasattr(a, "to_dict") else dict(a)
        d["accept"] = _default_accept(d)
        payload.append(d)
    p = Proposal(pid=pid, group=group, project=project, source=source,
                 created=created, status="draft", axioms=payload)
    write(root, p)
    return p


def path_for(root: Path, group: str, pid: str) -> Path:
    return proposals_dir(root, group) / f"{pid}.yaml"


def write(root: Path, p: Proposal) -> Path:
    out = path_for(root, p.group, p.pid)
    out.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "id": p.pid, "group": p.group, "project": p.project, "source": p.source,
        "created": p.created, "status": p.status,
        **({"approved_by": p.approved_by, "approved_at": p.approved_at}
           if p.approved_by else {}),
        "axioms": p.axioms,
    }
    out.write_text(
        HEADER.format(status=p.status.upper(), source=p.source, group=p.group,
                      project=p.project, created=p.created, pid=p.pid)
        + "\n" + yaml.safe_dump(body, sort_keys=False, width=100), encoding="utf-8")
    return out


def read(root: Path, group: str, pid: str) -> Proposal:
    f = path_for(root, group, pid)
    if not f.exists():
        raise FileNotFoundError(f"no proposal '{pid}' in {group}")
    d = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    return Proposal(pid=d["id"], group=d["group"], project=d["project"],
                    source=d["source"], created=d["created"], status=d["status"],
                    axioms=d.get("axioms") or [],
                    approved_by=d.get("approved_by", ""),
                    approved_at=d.get("approved_at", ""))


def listing(root: Path, group: str) -> list[Proposal]:
    d = proposals_dir(root, group)
    if not d.exists():
        return []
    out = []
    for f in sorted(d.glob("*.yaml")):
        try:
            out.append(read(root, group, f.stem))
        except Exception:
            continue
    return out


# ---------------------------------------------------------------- approve ---
def apply_to_extension(root: Path, p: Proposal) -> tuple[Path, dict[str, int]]:
    """Merge accepted axioms into the group extension.

    Additive by design: an approved term is never silently removed by a later
    proposal, because something downstream may already depend on it. Removing a
    term is a deliberate edit of extension.yaml.
    """
    ext_path = Path(root) / "groups" / p.group / "ontology" / "extension.yaml"
    ext = yaml.safe_load(ext_path.read_text(encoding="utf-8")) if ext_path.exists() else {}
    ext = ext or {}
    classes = ext.setdefault("classes", {})
    relations = ext.setdefault("relations", [])
    applied = {"classes": 0, "properties": 0, "identities": 0, "relations": 0}
    skipped: list[str] = []

    # A property, identity or relation cannot conjure the class it belongs to.
    #
    # Every axiom used to be applied independently, and `classes.setdefault(cls)`
    # meant an accepted `Supply.cost` created a class `Supply` — with no label, no
    # description and no identity — after the `Supply` class axiom had been
    # rejected for having no unique key. The rejected term came back through the
    # side door, minus everything that made it reviewable, and then failed
    # `validate_topology` as a class with no identity. Rejecting a class has to
    # reject what hangs off it, or rejection means nothing.
    from pf.ontology.model import load_ontology

    # Already-real classes are the platform ontology's plus anything a previous
    # approval put in this extension; a proposal that adds only a property to an
    # existing class must still land.
    known = set(classes) | set(load_ontology().classes)
    approved_classes = known | {a["subject"] for a in p.accepted
                                if a["kind"] == "class"}

    def _class(name: str, axiom: dict[str, Any]) -> dict[str, Any] | None:
        if name not in approved_classes:
            skipped.append(f"{axiom['kind']} {axiom['subject']} "
                           f"(class `{name}` was not approved)")
            return None
        return classes.setdefault(name, {})

    for a in p.accepted:
        kind = a["kind"]
        if kind == "class" and a.get("action") == "add":
            spec = classes.setdefault(a["subject"], {})
            spec.setdefault("label", a["subject"])
            spec.setdefault("description",
                            f"Induced from `{a.get('table')}` and approved by "
                            f"{p.approved_by or 'a steward'}.")
            if a.get("parent"):
                spec["parent"] = a["parent"]
            if a.get("identity"):
                spec["identity"] = a["identity"]
            applied["classes"] += 1

        elif kind == "identity":
            cls = a["subject"]
            # A scan sees the raw column; the platform ontology holds the modelled
            # name someone chose. Silently preferring the scan replaces a decision
            # with an accident, and every derived join follows the wrong column.
            if a.get("conflicts_with_existing") and not a.get("override"):
                skipped.append(f"identity {cls} → {a['property']} "
                               f"(would override a curated identity; set override: true)")
                continue
            spec = _class(cls, a)
            if spec is None:
                continue
            spec["identity"] = a["property"]
            applied["identities"] += 1

        elif kind == "property":
            cls, prop = a["subject"].split(".", 1)
            spec = _class(cls, a)
            if spec is None:
                continue
            props = spec.setdefault("properties", {})
            entry = {"datatype": a.get("datatype", "string")}
            if a.get("role"):
                entry["role"] = a["role"]
            if a.get("required"):
                entry["required"] = True
            props[prop] = entry
            applied["properties"] += 1

        elif kind == "relation":
            name = a["subject"]
            missing = [c for c in (a["domain"], a["range"])
                       if c not in approved_classes]
            if missing:
                skipped.append(f"relation {name} (class(es) {missing} not approved)")
                continue
            relations[:] = [r for r in relations if r.get("name") != name]
            relations.append({
                "name": name, "domain": a["domain"], "range": a["range"],
                "cardinality": a["cardinality"],
                "label": a.get("label", ""), "inverse": a.get("inverse", ""),
                "description": a.get("rationale", ""),
            })
            applied["relations"] += 1

    ext.setdefault("version", 1)
    # Recorded before the write, not after. It was set on the dict once the file
    # had already been serialised, so every skip an approval made — an identity
    # that would have overridden a curated one, a property whose class was
    # rejected — was reported to the terminal and then thrown away. The reason an
    # axiom did not land is the part worth keeping.
    if skipped:
        ext["_skipped_on_last_approval"] = skipped
    else:
        ext.pop("_skipped_on_last_approval", None)
    ext_path.parent.mkdir(parents=True, exist_ok=True)
    ext_path.write_text(
        "# Group ontology extension — approved additions only.\n"
        "#\n"
        "# Layers over the platform ontology; never replaces it. Terms here are\n"
        "# specific to this group, so another company never inherits a word that\n"
        "# means nothing to them. Written by `pf ontology approve`; hand edits are\n"
        "# expected and preserved.\n\n"
        + yaml.safe_dump(ext, sort_keys=False, width=100), encoding="utf-8")
    return ext_path, applied


def approve(root: Path, group: str, pid: str, by: str = "") -> tuple[Proposal, Path, dict[str, int]]:
    p = read(root, group, pid)
    if p.status == "applied":
        raise ValueError(f"proposal '{pid}' is already applied")
    if not p.accepted:
        raise ValueError(f"proposal '{pid}' has no axioms marked `accept: true`")
    p.approved_by = by or getpass.getuser()
    p.approved_at = _now()
    p.status = "applied"
    ext_path, applied = apply_to_extension(root, p)
    write(root, p)
    return p, ext_path, applied


def diff_against(root: Path, group: str, p: Proposal) -> dict[str, list[str]]:
    """What approving would change, relative to the ontology in force today."""
    from pf.ontology.model import load_group_ontology

    onto = load_group_ontology(root, group)
    new_classes, new_props, new_rels, reused = [], [], [], []
    for a in p.accepted:
        if a["kind"] == "class":
            (reused if onto.has_class(a["subject"]) else new_classes).append(a["subject"])
        elif a["kind"] == "property":
            cls, prop = a["subject"].split(".", 1)
            if prop not in onto.properties_of(cls):
                new_props.append(a["subject"])
        elif a["kind"] == "relation" and not onto.relation(a["subject"]):
            new_rels.append(f"{a['domain']} → {a['range']} [{a['cardinality']}]")
    return {"new_classes": new_classes, "reused_classes": reused,
            "new_properties": new_props, "new_relations": new_rels}
