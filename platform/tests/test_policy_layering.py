"""Tests for the policy override layer.

Policy is the one part of the ontology that is genuinely local: vocabulary must
be shared or a roll-up adds two things that merely share a name, but what must
*hold* differs per entity — acme-eu answers to GDPR and acme-us does not.

Every case here is a way that layering could go wrong quietly. A layer that can
relax an inherited rule is not a layer, it is a bypass, and the failure would be
invisible until the incident the rule existed to prevent.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pf.ontology.model import (
    PolicyRelaxation,
    load_group_ontology,
    load_ontology,
    load_project_ontology,
)


def _policy_file(path: Path, policies: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"policies": policies}, sort_keys=False))


def _project(root: Path, group: str, project: str) -> Path:
    d = root / "groups" / group / "projects" / project / "governance"
    d.mkdir(parents=True, exist_ok=True)
    return d / "policy.yaml"


def _by_id(onto, pid: str):
    return next(p for p in onto.policies if p.id == pid)


def test_a_project_may_add_a_policy_of_its_own(tmp_path: Path) -> None:
    _policy_file(_project(tmp_path, "acme", "acme-eu"), [{
        "id": "gdpr-erasure-path",
        "intent": "A subject access request must have somewhere to land.",
        "constraint": "erasure_declared",
        "severity": "error",
        "enforced_by": ["pf.ontology.validate:erasure-path"],
    }])
    onto = load_project_ontology(tmp_path, "acme", "acme-eu")
    p = _by_id(onto, "gdpr-erasure-path")
    assert p.severity == "error"
    assert p.scope == "project:acme/acme-eu"


def test_a_project_may_tighten_an_inherited_policy(tmp_path: Path) -> None:
    """`mart-declares-grain` ships as a warning; a project may make it fatal."""
    base = _by_id(load_ontology(), "mart-declares-grain")
    assert base.severity == "warning", "fixture assumption changed"

    _policy_file(_project(tmp_path, "acme", "acme-eu"),
                 [{"id": "mart-declares-grain", "severity": "error"}])
    p = _by_id(load_project_ontology(tmp_path, "acme", "acme-eu"), "mart-declares-grain")
    assert p.severity == "error"
    assert p.scope == "project:acme/acme-eu"
    # Tightening keeps everything the base declared.
    assert p.constraint == base.constraint
    assert base.enforced_by[0] in p.enforced_by


def test_a_project_cannot_relax_an_inherited_policy(tmp_path: Path) -> None:
    _policy_file(_project(tmp_path, "acme", "acme-us"),
                 [{"id": "pii-not-in-consumption", "severity": "warning"}])
    with pytest.raises(PolicyRelaxation, match="lowers severity"):
        load_project_ontology(tmp_path, "acme", "acme-us")


def test_a_project_cannot_retarget_an_inherited_policy(tmp_path: Path) -> None:
    """Narrowing `applies_to` is a partial delete wearing a refinement's clothes."""
    _policy_file(_project(tmp_path, "acme", "acme-us"), [{
        "id": "pii-not-in-consumption",
        "severity": "error",
        "applies_to": {"role_glob": "pii_email"},
    }])
    with pytest.raises(PolicyRelaxation, match="redefines 'applies_to'"):
        load_project_ontology(tmp_path, "acme", "acme-us")


def test_a_project_may_add_evidence_without_claiming_the_policy(tmp_path: Path) -> None:
    """Naming another enforcing artifact is not a tightening, so the severity's
    owner stays where it was — otherwise every project would appear to own every
    policy it merely helps enforce."""
    _policy_file(_project(tmp_path, "acme", "acme-us"), [{
        "id": "mart-declares-grain",
        "enforced_by": ["pf.local:extra-check"],
        "evidence": ["local-report.md"],
    }])
    p = _by_id(load_project_ontology(tmp_path, "acme", "acme-us"), "mart-declares-grain")
    assert "pf.local:extra-check" in p.enforced_by
    assert "local-report.md" in p.evidence
    assert p.scope == "platform"


def test_sisters_do_not_inherit_each_others_policy(tmp_path: Path) -> None:
    """The whole point: acme-eu may be stricter without moving acme-us."""
    _policy_file(_project(tmp_path, "acme", "acme-eu"),
                 [{"id": "mart-declares-grain", "severity": "error"}])
    eu = _by_id(load_project_ontology(tmp_path, "acme", "acme-eu"), "mart-declares-grain")
    us = _by_id(load_project_ontology(tmp_path, "acme", "acme-us"), "mart-declares-grain")
    assert (eu.severity, us.severity) == ("error", "warning")


def test_a_group_policy_reaches_every_sister(tmp_path: Path) -> None:
    _policy_file(tmp_path / "groups" / "acme" / "ontology" / "policy.yaml",
                 [{"id": "mart-declares-grain", "severity": "error"}])
    for project in ("acme-us", "acme-eu"):
        p = _by_id(load_project_ontology(tmp_path, "acme", project), "mart-declares-grain")
        assert p.severity == "error"
        assert p.scope == "group:acme"


def test_a_project_cannot_relax_what_its_group_tightened(tmp_path: Path) -> None:
    _policy_file(tmp_path / "groups" / "acme" / "ontology" / "policy.yaml",
                 [{"id": "mart-declares-grain", "severity": "error"}])
    _policy_file(_project(tmp_path, "acme", "acme-us"),
                 [{"id": "mart-declares-grain", "severity": "warning"}])
    with pytest.raises(PolicyRelaxation):
        load_project_ontology(tmp_path, "acme", "acme-us")


def test_overlaying_never_mutates_the_cached_platform_ontology(tmp_path: Path) -> None:
    """`load_ontology` is lru_cached and shared by every caller. An overlay that
    wrote through to it would leak one project's policy into every other, and the
    test that caught it would be somewhere else entirely."""
    before = [(p.id, p.severity, p.scope) for p in load_ontology().policies]
    _policy_file(_project(tmp_path, "acme", "acme-eu"), [
        {"id": "mart-declares-grain", "severity": "error"},
        {"id": "gdpr-erasure-path", "intent": "x", "constraint": "erasure_declared"},
    ])
    load_project_ontology(tmp_path, "acme", "acme-eu")
    assert [(p.id, p.severity, p.scope) for p in load_ontology().policies] == before


def test_a_group_with_no_extension_still_gets_its_policy(tmp_path: Path) -> None:
    """The early return for a missing extension.yaml is the path most likely to
    hand back the shared cached object by accident."""
    _policy_file(tmp_path / "groups" / "solo" / "ontology" / "policy.yaml",
                 [{"id": "mart-declares-grain", "severity": "error"}])
    onto = load_group_ontology(tmp_path, "solo")
    assert _by_id(onto, "mart-declares-grain").severity == "error"
    assert _by_id(load_ontology(), "mart-declares-grain").severity == "warning"


# ------------------------------------------------------- scaffold seam ----
def test_the_governance_capability_is_on_by_default() -> None:
    """A policy overlay that only reached projects whose author remembered a
    flag is how one project ends up governed and seven do not."""
    from pf.capabilities import CAPABILITIES, defaults

    assert "governance" in defaults()
    assert "governance/policy.yaml" in CAPABILITIES["governance"].files


def test_the_seeded_overlay_changes_no_verdict(tmp_path: Path) -> None:
    """Scaffolding a project, or backfilling this into eight existing ones, must
    not move a single severity. The stub exists to be found, not to take effect
    on arrival."""
    from pf.capabilities import CAPABILITIES
    from pf.capabilities import apply as apply_capability

    pdir = tmp_path / "groups" / "acme" / "projects" / "acme-us"
    pdir.mkdir(parents=True)
    apply_capability(CAPABILITIES["governance"], tmp_path, pdir,
                     {"group": "acme", "project": "acme-us", "module": "acme_us"})

    seeded = pdir / "governance" / "policy.yaml"
    assert seeded.exists()
    assert (yaml.safe_load(seeded.read_text()) or {}).get("policies") == []

    resolved = load_project_ontology(tmp_path, "acme", "acme-us")
    assert [(p.id, p.severity) for p in resolved.policies] == \
           [(p.id, p.severity) for p in load_ontology().policies]


def test_reapplying_the_capability_preserves_an_edited_overlay(tmp_path: Path) -> None:
    """`pf capability-add` bypasses the backfill's all-or-nothing guard, so the
    only thing standing between a re-apply and someone's policy file is
    `Capability.preserve`."""
    from pf.capabilities import CAPABILITIES
    from pf.capabilities import apply as apply_capability

    pdir = tmp_path / "groups" / "acme" / "projects" / "acme-eu"
    ctx = {"group": "acme", "project": "acme-eu", "module": "acme_eu"}
    pdir.mkdir(parents=True)
    apply_capability(CAPABILITIES["governance"], tmp_path, pdir, ctx)

    mine = pdir / "governance" / "policy.yaml"
    mine.write_text(yaml.safe_dump(
        {"policies": [{"id": "mart-declares-grain", "severity": "error"}]}))

    apply_capability(CAPABILITIES["governance"], tmp_path, pdir, ctx)

    assert _by_id(load_project_ontology(tmp_path, "acme", "acme-eu"),
                  "mart-declares-grain").severity == "error"


def test_a_new_project_is_scaffolded_with_the_overlay(tmp_path: Path) -> None:
    from pf.capabilities import CAPABILITIES, defaults, resolve
    from pf.capabilities import apply as apply_capability

    pdir = tmp_path / "groups" / "acme" / "projects" / "acme-new"
    pdir.mkdir(parents=True)
    for cap in resolve(defaults()):
        if cap.name != "governance":
            continue
        apply_capability(cap, tmp_path, pdir,
                         {"group": "acme", "project": "acme-new", "module": "acme_new"})
    assert (pdir / "governance" / "policy.yaml").exists()
    assert CAPABILITIES["governance"].gate["impact_required"] == \
           ["**/governance/policy.yaml"]
