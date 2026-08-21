"""Obligations declared by a capability, and the guard they layer through.

The property that matters is the one that makes this safe to be generic: a
capability may *tighten* the platform floor and may never relax it. Everything
else here protects the honesty of the chain — that a policy claiming enforcement
names something real, and that an unenforced one says so instead of going quiet.
"""

from __future__ import annotations

import shutil

import pytest
import yaml
from conftest import REPO_ROOT
from pf.capabilities import (
    CAPABILITIES,
    Capability,
    defaults,
    policy_additions,
    resolve,
    write_capability_policies,
)
from pf.ontology.model import PolicyRelaxation, load_ontology

ONTOLOGY = REPO_ROOT / "platform" / "src" / "pf" / "ontology"


def _ontology_dir(tmp_path, overlay_policies):
    """A real ontology with a synthetic capability overlay beside it."""
    d = tmp_path / "ontology"
    d.mkdir()
    for name in ("concepts.yaml", "topology.yaml", "policy.yaml"):
        shutil.copy(ONTOLOGY / name, d / name)
    (d / "policy.capabilities.yaml").write_text(
        yaml.safe_dump({"policies": overlay_policies}))
    return d


# ------------------------------------------------------------- the guard ----
def test_a_capability_may_not_relax_the_floor(tmp_path) -> None:
    """The whole reason this seam is safe to hand to any future capability."""
    d = _ontology_dir(tmp_path, [
        # `secrets-never-in-context` is `error` in the floor.
        {"id": "secrets-never-in-context", "severity": "info"},
    ])
    with pytest.raises(PolicyRelaxation, match="secrets-never-in-context"):
        load_ontology(d)


def test_a_capability_may_tighten(tmp_path) -> None:
    """`mart-declares-grain` ships as a warning; a capability may make it block."""
    d = _ontology_dir(tmp_path, [
        {"id": "mart-declares-grain", "severity": "error"},
    ])
    onto = load_ontology(d)
    assert next(p for p in onto.policies if p.id == "mart-declares-grain").severity == "error"


def test_a_capability_may_not_retarget_an_inherited_policy(tmp_path) -> None:
    """Narrowing `applies_to` reads as a refinement and is a partial delete."""
    d = _ontology_dir(tmp_path, [
        {"id": "pii-not-in-consumption", "applies_to": {"role_glob": "pii_email"}},
    ])
    with pytest.raises(PolicyRelaxation, match="applies_to"):
        load_ontology(d)


def test_a_new_policy_arrives_at_capability_scope(tmp_path) -> None:
    d = _ontology_dir(tmp_path, [
        {"id": "brand-new-rule", "intent": "x", "constraint": "y", "severity": "warning"},
    ])
    onto = load_ontology(d)
    p = next(p for p in onto.policies if p.id == "brand-new-rule")
    assert p.scope == "capability"


# ------------------------------------------------------------ the union -----
def test_policies_reach_the_overlay() -> None:
    caps = resolve(defaults())
    ids = {p["id"] for p in policy_additions(caps)}
    assert "entity-isolation-enforced" in ids
    assert "money-amount-bounded" in ids


def test_two_capabilities_naming_one_obligation_produce_one_entry() -> None:
    """A duplicate id would make the generated file fail its own layering check."""
    shared = {"id": "shared-rule", "intent": "i", "constraint": "c"}
    caps = [Capability(name="a", description="d", policies=(shared,)),
            Capability(name="b", description="d", policies=(shared,))]
    out = policy_additions(caps)
    assert [p["id"] for p in out] == ["shared-rule"]
    assert out[0]["_capability"] == "a"


def test_each_entry_records_which_capability_declared_it() -> None:
    for entry in policy_additions(resolve(defaults())):
        assert entry["_capability"] in CAPABILITIES, entry["id"]


# ----------------------------------------------------------- generation -----
def test_generation_is_deterministic(tmp_path) -> None:
    """A generated file that reshuffles itself is a diff nobody can read."""
    root = tmp_path
    (root / "platform" / "src" / "pf" / "ontology").mkdir(parents=True)
    first = write_capability_policies(root).read_text()
    second = write_capability_policies(root).read_text()
    assert first == second


def test_the_committed_overlay_matches_the_registry(tmp_path) -> None:
    """`pf bootstrap` regenerates this; a stale one is a rule nobody declares."""
    root = tmp_path
    (root / "platform" / "src" / "pf" / "ontology").mkdir(parents=True)
    want = write_capability_policies(root).read_text()
    assert (ONTOLOGY / "policy.capabilities.yaml").read_text() == want


# -------------------------------------------------------------- honesty ----
def test_every_declared_policy_states_its_intent() -> None:
    """A rule with no reason is a rule the next person deletes or works around."""
    for entry in policy_additions(resolve(defaults())):
        assert entry.get("intent", "").strip(), entry["id"]
        assert entry.get("constraint"), entry["id"]


def test_enforcement_claims_name_something_locatable() -> None:
    """Claiming enforcement that does not exist ends the conversation."""
    for entry in policy_additions(resolve(defaults())):
        for claim in entry.get("enforced_by") or []:
            # `module:check`, `file.yaml:section`, or a repo path.
            head = claim.split(":")[0]
            assert head.startswith("pf.") or (REPO_ROOT / head).exists(), claim


def test_unenforced_policies_are_declared_unenforced() -> None:
    """The honest state is an empty list, not a plausible-looking claim."""
    by_id = {p["id"]: p for p in policy_additions(resolve(defaults()))}
    assert by_id["money-amount-bounded"]["enforced_by"] == []
    assert by_id["source-declares-freshness"]["enforced_by"] == []
