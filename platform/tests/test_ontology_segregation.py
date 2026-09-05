"""Tests for the seam between the three ontology layers.

    platform   universal vocabulary          platform/src/pf/ontology/*.yaml
    group      one family's own terms        groups/<g>/ontology/extension.yaml
    project    physical bindings             <project>/contracts/annotations.yaml

The layering is what keeps companies independent: a class one group invented
must never be visible to a sister, and the platform base must never quietly
absorb a group's term. Every test here checks a direction terms could leak —
up into the base, sideways into a sister, or down into a project that speaks
a different vocabulary. The real group and project artefacts in the repo are
test subjects alongside synthetic ones, so a leak introduced by hand-editing
a YAML file fails here before it reaches CI.

Run locally before committing anything that touches an ontology surface:

    uv run pytest platform/tests/test_ontology_segregation.py -q

The pre-commit hook runs this file automatically when staged paths touch
`platform/src/pf/ontology/`, any `groups/*/ontology/`, or a project's
`contracts/annotations.yaml`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pf.ontology.annotate import Annotation, load_annotations
from pf.ontology.model import Ontology, load_group_ontology, load_ontology
from pf.ontology.validate import (
    _ontology_for,
    pii_columns,
    validate_instance,
    validate_project,
    validate_sources,
    validate_topology,
)

ROOT = Path(__file__).resolve().parents[2]
GROUPS_DIR = ROOT / "groups"

# Discovered, not listed: a group added tomorrow is covered without anyone
# editing this file.
ALL_GROUPS = sorted(p.parent.parent.name for p in GROUPS_DIR.glob("*/ontology/instance.yaml"))
EXTENDED_GROUPS = sorted(p.parent.parent.name for p in GROUPS_DIR.glob("*/ontology/extension.yaml"))

MENTAL_HEALTH = GROUPS_DIR / "hospital" / "projects" / "mental-health"


def _errors(issues) -> list:
    return [i for i in issues if i.severity == "error"]


def _invented(merged: Ontology, base: Ontology) -> set[str]:
    """Class names a group added beyond the platform vocabulary."""
    return set(merged.classes) - set(base.classes)


def _write_extension(root: Path, group: str, doc: dict) -> Path:
    d = root / "groups" / group / "ontology"
    d.mkdir(parents=True, exist_ok=True)
    (d / "extension.yaml").write_text(yaml.safe_dump(doc))
    return d / "extension.yaml"


# ------------------------------------------------- repo level: the base ----
def test_platform_base_defines_no_group_invented_class() -> None:
    """Promoting a group term to the platform is a deliberate act that includes
    removing it from the extension. A class defined in both places would mean a
    sister group silently inherited a word that means nothing to it — the exact
    failure the layering exists to prevent."""
    platform_classes = set(load_ontology().classes)
    for group in EXTENDED_GROUPS:
        ext = yaml.safe_load((GROUPS_DIR / group / "ontology" / "extension.yaml").read_text()) or {}
        for name in ext.get("classes") or {}:
            spec = ext["classes"][name] or {}
            # Shadowing a platform class to add properties is the supported
            # pattern; declaring a *parent* means the extension thinks it owns
            # the definition — that name must not also exist in the base.
            if name in platform_classes and spec.get("parent") in (None, load_ontology().classes[name].parent):
                continue
            assert name not in platform_classes, (
                f"'{name}' is defined by both the platform ontology and "
                f"groups/{group} — promote it or extend it, not both"
            )


def test_platform_ontology_is_internally_coherent() -> None:
    """The base every group layers over has to stand on its own: no class
    without an identity, no relation pointing at a class that does not exist."""
    assert _errors(validate_topology(load_ontology())) == []


def test_loading_every_group_leaves_the_cached_base_untouched() -> None:
    """`load_ontology()` is lru-cached and shared. If a group merge ever mutated
    it instead of copying, the first group loaded would leak its classes into
    every ontology loaded afterwards — cross-company contamination through a
    cache, invisible in any YAML file."""
    load_ontology.cache_clear()
    pristine = set(load_ontology().classes)
    for group in ALL_GROUPS:
        load_group_ontology(ROOT, group)
    after = load_ontology()
    assert set(after.classes) == pristine
    for group in EXTENDED_GROUPS:
        merged = load_group_ontology(ROOT, group)
        assert _invented(merged, after).isdisjoint(after.classes)


# ------------------------------------- group level: layering, not replacing ----
def test_extension_layers_over_the_base_never_replaces_it(tmp_path: Path) -> None:
    """A merged ontology is the platform plus the group — every platform class,
    role and relation must survive the merge intact."""
    base = load_ontology()
    _write_extension(
        tmp_path,
        "g",
        {
            "version": 1,
            "classes": {
                "Widget": {
                    "parent": "Product",
                    "identity": "widget_id",
                    "properties": {"widget_id": {"role": "natural_key", "required": True}},
                }
            },
        },
    )
    merged = load_group_ontology(tmp_path, "g")

    assert set(base.classes) <= set(merged.classes)
    assert set(base.roles) <= set(merged.roles)
    assert {r.name for r in base.relations} <= {r.name for r in merged.relations}
    assert merged.has_class("Widget")
    assert merged.is_a("Widget", "Product")
    assert not base.has_class("Widget")


def test_extension_property_additions_keep_the_platform_class_intact(tmp_path: Path) -> None:
    """A group may add properties to a platform class without redefining it:
    the platform's own properties, parent and identity must all survive."""
    base = load_ontology()
    _write_extension(
        tmp_path,
        "g",
        {
            "version": 1,
            "classes": {"Order": {"properties": {"loyalty_tier": {"datatype": "string", "role": "status_enum"}}}},
        },
    )
    merged = load_group_ontology(tmp_path, "g")

    order = merged.classes["Order"]
    assert set(base.classes["Order"].properties) <= set(order.properties)
    assert "loyalty_tier" in order.properties
    assert order.parent == base.classes["Order"].parent
    assert order.identity == base.classes["Order"].identity


@pytest.mark.parametrize("group", EXTENDED_GROUPS)
def test_no_real_extension_reparents_a_platform_class(group: str) -> None:
    """Rebinding identity to a physical column is an accepted pattern; moving a
    platform class to a different parent is not — it rewrites the shared
    hierarchy for one group, so `is_a` and the topology stop meaning the same
    thing across sisters."""
    base = load_ontology()
    merged = load_group_ontology(ROOT, group)
    for name in set(merged.classes) & set(base.classes):
        assert merged.classes[name].parent == base.classes[name].parent, (
            f"groups/{group} re-parents platform class '{name}'"
        )


def test_extension_relation_override_replaces_by_name(tmp_path: Path) -> None:
    """A group restating a platform relation gets exactly one relation of that
    name — the group's version — and every other platform relation untouched."""
    base = load_ontology()
    target = base.relations[0]
    _write_extension(
        tmp_path,
        "g",
        {
            "version": 1,
            "relations": [
                {"name": target.name, "domain": target.domain, "range": target.range, "cardinality": "MANY_TO_MANY"}
            ],
        },
    )
    merged = load_group_ontology(tmp_path, "g")

    hits = [r for r in merged.relations if r.name == target.name]
    assert len(hits) == 1 and hits[0].cardinality == "MANY_TO_MANY"
    assert len(merged.relations) == len(base.relations)


def test_a_group_without_an_extension_speaks_pure_platform(tmp_path: Path) -> None:
    """No extension file means no vocabulary of one's own — not an error, and
    not somebody else's vocabulary either."""
    merged = load_group_ontology(tmp_path, "no_such_group")
    base = load_ontology()
    assert set(merged.classes) == set(base.classes)
    assert {r.name for r in merged.relations} == {r.name for r in base.relations}


def test_policy_is_platform_law_no_extension_can_amend_it(tmp_path: Path) -> None:
    """Governance does not federate. An extension.yaml that tries to declare
    policies is ignored: the merged ontology carries exactly the platform's
    policies, so no group can weaken a control by editing its own files."""
    base = load_ontology()
    _write_extension(
        tmp_path,
        "g",
        {
            "version": 1,
            "classes": {"Widget": {"parent": "Product"}},
            "policies": [{"id": "backdoor", "intent": "weaken", "constraint": "none"}],
        },
    )
    merged = load_group_ontology(tmp_path, "g")
    assert [p.id for p in merged.policies] == [p.id for p in base.policies]
    assert merged.policy("backdoor") is None


@pytest.mark.parametrize("group", EXTENDED_GROUPS)
def test_every_merged_group_ontology_is_internally_coherent(group: str) -> None:
    """The merge must produce something as sound as the base: every extension
    class resolves its parent, carries an identity, and every group relation
    points at classes that exist in that group's merged vocabulary."""
    assert _errors(validate_topology(load_group_ontology(ROOT, group))) == []


# ------------------------------------------- sister isolation: no transfer ----
def test_sister_groups_never_see_each_others_classes() -> None:
    """The router rule, executable: business logic does not transfer between
    entities. Every class a group invented must be invisible from every other
    group's merged ontology."""
    base = load_ontology()
    invented = {g: _invented(load_group_ontology(ROOT, g), base) for g in ALL_GROUPS}
    for g, own in invented.items():
        for other in ALL_GROUPS:
            if other == g:
                continue
            visible = set(load_group_ontology(ROOT, other).classes)
            leaked = own & visible
            assert not leaked, f"classes {sorted(leaked)} from {g} visible in {other}"


def test_group_relations_do_not_travel() -> None:
    base = {r.name for r in load_ontology().relations}
    invented = {g: {r.name for r in load_group_ontology(ROOT, g).relations} - base for g in ALL_GROUPS}
    for g, own in invented.items():
        for other in ALL_GROUPS:
            if other == g:
                continue
            visible = {r.name for r in load_group_ontology(ROOT, other).relations}
            assert own.isdisjoint(visible), f"relations from {g} visible in {other}"


# --------------------------- instance: selecting from the platform, only ----
@pytest.mark.parametrize("group", ALL_GROUPS)
def test_every_group_instance_selects_only_platform_classes(group: str) -> None:
    """Rule 6 against the real files: instance.yaml says which *platform*
    concepts this group models. It is a subset declaration, not a place to
    define anything."""
    issues = validate_instance(GROUPS_DIR / group / "ontology" / "instance.yaml")
    assert _errors(issues) == []


def test_an_extension_class_cannot_be_selected_in_the_instance(tmp_path: Path) -> None:
    """`Patient` is hospital vocabulary and lives in hospital's extension. An
    instance.yaml naming it must fail even though the class is real for that
    group — the instance file speaks platform, and letting extension terms in
    would blur which layer owns a word."""
    inst = tmp_path / "instance.yaml"
    inst.write_text(yaml.safe_dump({"group": "g", "classes": ["Party", "Patient"]}))
    issues = validate_instance(inst)
    assert [i.rule for i in _errors(issues)] == ["unknown-class"]
    assert "Patient" in _errors(issues)[0].message


def test_a_missing_instance_is_reported_not_ignored(tmp_path: Path) -> None:
    issues = validate_instance(tmp_path / "instance.yaml")
    assert [i.rule for i in _errors(issues)] == ["missing-instance"]


# ------------------- project level: bound to its own group, and only that ----
def test_project_ontology_is_derived_from_its_path(tmp_path: Path) -> None:
    """A project under groups/<g>/projects/<p> validates against platform+<g>;
    a directory outside that shape gets the bare platform. The group is never
    a parameter someone can pass wrong — it is read off the path."""
    assert _ontology_for(MENTAL_HEALTH).has_class("Patient")
    assert not _ontology_for(tmp_path).has_class("Patient")
    # A path that *looks* projecty but names no real group falls back cleanly.
    orphan = tmp_path / "groups" / "ghost" / "projects" / "p"
    orphan.mkdir(parents=True)
    assert set(_ontology_for(orphan).classes) == set(load_ontology().classes)


def test_mental_health_conforms_to_its_own_group_ontology() -> None:
    """The live project must validate against platform+hospital with no errors.
    If this fails, either an annotation drifted or somebody removed a hospital
    concept the project still binds to."""
    assert _errors(validate_project(MENTAL_HEALTH)) == []


def test_project_annotations_fail_under_every_sister_ontology() -> None:
    """The sharpest segregation check in the file: mental-health's real
    annotations, validated under each sister group's merged ontology, must
    fail for every resource bound to a hospital concept. If this ever passes
    under a sister, hospital vocabulary has leaked into that group's layer."""
    anns = load_annotations(MENTAL_HEALTH / "contracts" / "annotations.yaml")
    assert anns, "mental-health has no annotations to test against"
    base = load_ontology()
    hospital_bound = [a for a in anns if a.concept in _invented(load_group_ontology(ROOT, "hospital"), base)]
    assert hospital_bound, "expected mental-health to bind hospital-invented concepts"

    for group in ALL_GROUPS:
        if group == "hospital":
            continue
        issues = validate_sources(anns, load_group_ontology(ROOT, group))
        unknown = {i.subject for i in issues if i.rule == "unknown-class"}
        for a in hospital_bound:
            assert a.resource in unknown, (
                f"'{a.concept}' ({a.resource}) validated under groups/{group} — "
                f"hospital vocabulary is visible to a sister"
            )


def test_the_bare_platform_rejects_group_concepts() -> None:
    """Same direction, bottom of the ladder: an annotation speaking a group's
    word means nothing to the platform alone."""
    ann = Annotation(resource="r", concept="Patient", roles={"id": "natural_key"})
    assert any(i.rule == "unknown-class" for i in validate_sources([ann], load_ontology()))
    assert not any(i.rule == "unknown-class" for i in validate_sources([ann], load_group_ontology(ROOT, "hospital")))


def test_group_declared_pii_is_only_visible_through_the_group_ontology(tmp_path: Path) -> None:
    """A role a group marks as PII must be honoured wherever that group's
    ontology is in force — and must not exist at all outside it. Validating a
    project with the wrong layer would not just mislabel columns, it would
    silently drop the PII flag that keeps values out of review artefacts."""
    _write_extension(
        tmp_path, "g", {"version": 1, "roles": {"medical_record_number": {"datatype": "string", "pii": True}}}
    )
    merged = load_group_ontology(tmp_path, "g")
    ann = Annotation(resource="r", concept="Order", roles={"id": "natural_key", "mrn": "medical_record_number"})

    assert ("r", "mrn", "medical_record_number") in pii_columns([ann], merged)
    assert pii_columns([ann], load_ontology()) == []
    assert merged.roles["medical_record_number"].review_intent == "none"
    assert any(i.rule == "unknown-role" for i in validate_sources([ann], load_ontology()))
    assert not any(i.rule == "unknown-role" for i in validate_sources([ann], merged))
