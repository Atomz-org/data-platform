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


def _fake_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Make `tmp_path` look like a repo root, and stand inside it.

    `pf.obs.repo_root` walks up from cwd for a directory holding both
    `platform/` and `groups/`, so anything that resolves the root itself —
    rather than using the one it was passed — lands here instead of in the real
    checkout.
    """
    (tmp_path / "platform").mkdir(exist_ok=True)
    (tmp_path / "groups").mkdir(exist_ok=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


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


def test_bootstrap_backfills_the_overlay_into_a_project_without_one(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The path that reaches projects that already existed when this shipped.

    `pf new-project` covers new ones; every project older than the capability
    depends on this step, which is exactly the hole `pf bootstrap` was built to
    close for platform steps.

    `_fake_root` is not ceremony: the backfill merges gate rules through
    `pf.cli._merge_gate_rules`, which resolves the repo from *cwd* rather than
    from the `root` it was handed. Without the chdir this test writes into the
    real gate.capabilities.yaml.
    """
    from pf.scaffold.bootstrap import _bootstrap_capabilities

    pdir = _fake_root(tmp_path, monkeypatch) / "groups" / "acme" / "projects" / "acme-us"
    pdir.mkdir(parents=True)
    results = {r.name: r for r in _bootstrap_capabilities(tmp_path, "acme", "acme-us")}

    assert "capability:governance" in results
    assert (pdir / "governance" / "policy.yaml").exists()


def test_bootstrap_leaves_an_existing_overlay_alone(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Backfill must never rewrite a policy file someone has written into."""
    from pf.scaffold.bootstrap import _bootstrap_capabilities

    pdir = _fake_root(tmp_path, monkeypatch) / "groups" / "acme" / "projects" / "acme-eu"
    (pdir / "governance").mkdir(parents=True)
    mine = pdir / "governance" / "policy.yaml"
    _policy_file(mine, [{"id": "mart-declares-grain", "severity": "error"}])

    _bootstrap_capabilities(tmp_path, "acme", "acme-eu")

    assert _by_id(load_project_ontology(tmp_path, "acme", "acme-eu"),
                  "mart-declares-grain").severity == "error"


# --------------------------------------------------------------- the graph --
# The overlay is only real where it is read. `pf semantic policy` resolving at
# project scope while `pf kg build` stopped at the group meant the governance
# plane an agent walks was the family floor — so a project that raised a
# severity, or declared an obligation of its own, was governed by rules its own
# graph did not contain.

def _graph_policies(pdir: Path, group: str, project: str) -> dict[str, dict]:
    """Build a graph for `pdir` and return its Policy nodes by id."""
    import duckdb
    from pf.kg.build import build_graph

    build_graph(pdir, group=group, project=project)
    con = duckdb.connect(str(pdir / "kg" / "graph.duckdb"), read_only=True)
    try:
        rows = con.execute(
            "SELECT name, json_extract_string(props, '$.severity'), "
            "json_extract_string(props, '$.scope') "
            "FROM kg_nodes WHERE kind = 'Policy'"
        ).fetchall()
    finally:
        con.close()
    return {r[0]: {"severity": r[1], "scope": r[2]} for r in rows}


def test_graph_carries_the_projects_own_policy(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A policy only the project declares has to reach that project's graph."""
    root = _fake_root(tmp_path, monkeypatch)
    pdir = root / "groups" / "acme" / "projects" / "acme-eu"
    _policy_file(pdir / "governance" / "policy.yaml", [{
        "id": "gdpr-erasure-path",
        "intent": "A subject access request must have somewhere to land.",
        "constraint": "erasure_declared",
        "applies_to": {"role_glob": "pii_*"},
        "severity": "error",
    }])

    found = _graph_policies(pdir, "acme", "acme-eu")

    assert "gdpr-erasure-path" in found
    assert found["gdpr-erasure-path"]["scope"] == "project:acme/acme-eu"


def test_graph_carries_a_tightened_severity_and_says_who_set_it(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The graph must show the tightened severity, and attribute it.

    Severity alone is not enough: an agent reading `error` off the graph cannot
    tell an obligation this project took on from one the whole platform carries,
    and those warrant different conversations.
    """
    root = _fake_root(tmp_path, monkeypatch)
    pdir = root / "groups" / "acme" / "projects" / "acme-eu"
    _policy_file(pdir / "governance" / "policy.yaml",
                 [{"id": "mart-declares-grain", "severity": "error"}])

    platform_default = _by_id(load_ontology(), "mart-declares-grain").severity
    assert platform_default != "error", "fixture assumes the floor is looser"

    found = _graph_policies(pdir, "acme", "acme-eu")

    assert found["mart-declares-grain"]["severity"] == "error"
    assert found["mart-declares-grain"]["scope"] == "project:acme/acme-eu"


def test_a_sister_without_an_overlay_keeps_the_floor(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """One sister's overlay must not leak into another's graph.

    `load_ontology` is lru_cached and shared, so the leak this guards against
    would surface in a project that declared nothing at all.
    """
    root = _fake_root(tmp_path, monkeypatch)
    eu = root / "groups" / "acme" / "projects" / "acme-eu"
    _policy_file(eu / "governance" / "policy.yaml",
                 [{"id": "mart-declares-grain", "severity": "error"}])
    _graph_policies(eu, "acme", "acme-eu")

    us = root / "groups" / "acme" / "projects" / "acme-us"
    us.mkdir(parents=True, exist_ok=True)
    found = _graph_policies(us, "acme", "acme-us")

    assert found["mart-declares-grain"]["severity"] == \
        _by_id(load_ontology(), "mart-declares-grain").severity
    assert found["mart-declares-grain"]["scope"] == "platform"
    assert "gdpr-erasure-path" not in found
