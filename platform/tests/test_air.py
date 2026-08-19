"""The control catalogue, the coverage derivation, and the baseline gate.

Almost everything here runs against a **synthetic catalogue** — a corpus written
into tmp_path, described by a `CatalogueSource` the test registers itself. That
is not only isolation: it is the assertion that `pf.air` reads catalogues rather
than one framework. Every default is overridden somewhere below (a different
path, a different prefix, different frontmatter keys, a different id template),
so a hardcoded FINOS assumption creeping back into the parser fails a test.

The handful that read the vendored corpus assert the *contract* holds, never what
it currently contains — a test asserting "23 controls" fails the day upstream
publishes a 24th, which is upstream doing its job — and skip when it is absent.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from pf.air.catalogue import NotVendored, available, load, split_frontmatter
from pf.air.coverage import _resolve_artefact, assess
from pf.air.register import (
    Acceptance,
    RegisterError,
    gate,
    load_config,
    render_register,
    validate,
)
from pf.air.sources import (
    CatalogueSource,
    Frontmatter,
    InvalidSource,
    Layout,
    discover,
)
from pf.air.verify import verify

REPO = Path(__file__).resolve().parents[2]


# ------------------------------------------------------------- a fake corpus --
#: Deliberately unlike the built-in: its own path, prefix, directories, type
#: vocabulary and reference suffix. Nothing in `pf.air` may assume otherwise.
FAKE = CatalogueSource(
    name="fake",
    title="Fake Control Library",
    path="catalogues/fake",
    prefix="FKE",
    licence="CC0-1.0",
    attribution="",
    layout=Layout(risks="risk", controls="control", references="crosswalk"),
    frontmatter=Frontmatter(),
    risk_types={"SEC": "Security", "OP": "Operational"},
    control_types={"PREV": "Preventative", "DET": "Detective"},
)

RISK = """\
---
sequence: {seq}
title: {title}
layout: risk
doc-status: Approved-Specification
type: {type}
{refs}---

## Summary

{title} is a thing that can go wrong.

## Description

More prose. This paragraph must not appear in the summary.
"""

CONTROL = """\
---
sequence: {seq}
title: {title}
layout: mitigation
doc-status: Approved-Specification
type: {type}
mitigates:
{mitigates}{refs}---

## Purpose

{title} stops it.

---

## Key Principles

Not the summary.
"""

REGIME = """\
title: "Fake Regulation"
description: "For tests."
source_url: "https://example.invalid/"

entries:
  art-1:
    title: "Article 1 Record-keeping"
    url: "https://example.invalid/1"
  art-2:
    title: "Article 2 Oversight"
    url: "https://example.invalid/2"
"""


def build_corpus(root: Path, *, risks=None, controls=None, regime: str = REGIME,
                 src: CatalogueSource = FAKE) -> CatalogueSource:
    """Write a corpus for `src` under `root`, and return the source describing it."""
    base = root / src.path
    fm = src.frontmatter
    for d in (src.layout.risks, src.layout.controls, src.layout.references):
        # exist_ok: some fixtures build a corpus and then layer an ontology over
        # the same tmp_path, calling this twice.
        (base / d).mkdir(parents=True, exist_ok=True)
    (base / src.layout.references / "fake-reg.yml").write_text(regime)

    risks = risks if risks is not None else [(1, "SEC", "Leaky Agent", ["art-1"])]
    controls = controls if controls is not None else [
        (1, "PREV", "Plug The Leak", ["ri-1"], ["art-1", "art-2"])
    ]

    def _refs(keys):
        if not keys:
            return ""
        return f"fake-reg{fm.reference_suffix}:\n" + "".join(f"  - {k}\n" for k in keys)

    for seq, typ, title, refs in risks:
        name = f"ri-{seq}{fm.slug_separator}{title.lower().replace(' ', '-')}.md"
        (base / src.layout.risks / name).write_text(
            RISK.format(seq=seq, title=title, type=typ, refs=_refs(refs)))
    for seq, typ, title, mits, refs in controls:
        name = f"mi-{seq}{fm.slug_separator}{title.lower().replace(' ', '-')}.md"
        (base / src.layout.controls / name).write_text(
            CONTROL.format(seq=seq, title=title, type=typ,
                           mitigates="".join(f"  - {m}\n" for m in mits), refs=_refs(refs)))
    return src


@pytest.fixture(autouse=True)
def _only_the_fake_catalogue(monkeypatch):
    """Register the synthetic catalogue and nothing else, for every test here.

    `discover()` reads `BUILTIN` at call time, so this reaches every consumer —
    `load`, `assess`, `gate`, `render_register` — without any of them growing a
    `sources=` parameter for the benefit of tests. The vendored-corpus tests at
    the bottom opt back out.
    """
    monkeypatch.setattr("pf.air.sources.BUILTIN", (FAKE,))


@pytest.fixture
def real_catalogues(monkeypatch):
    monkeypatch.undo()


# ------------------------------------------------------------------ parsing --
def test_frontmatter_stops_at_the_first_closing_fence():
    """A `---` inside the prose body is a horizontal rule, not the fence."""
    meta, body = split_frontmatter("---\ntitle: X\n---\n\nintro\n\n---\n\nmore\n")
    assert meta == {"title": "X"}
    assert "more" in body


def test_ids_are_derived_from_type_and_sequence(tmp_path):
    build_corpus(tmp_path)
    c = load(tmp_path)
    assert set(c.risks) == {"FKE-SEC-1"}
    assert set(c.controls) == {"FKE-PREV-1"}
    assert c.controls["FKE-PREV-1"].slug == "mi-1"


def test_type_change_renames_the_control(tmp_path):
    """Upstream flipping PREV to DET is not cosmetic — it renames the control,
    and every air.yaml baseline naming the old id stops matching."""
    build_corpus(tmp_path, controls=[(16, "PREV", "Access Controls", [], [])])
    assert "FKE-PREV-16" in load(tmp_path).controls

    other = tmp_path / "other"
    other.mkdir()
    build_corpus(other, controls=[(16, "DET", "Access Controls", [], [])])
    assert "FKE-DET-16" in load(other).controls


def test_mitigates_resolves_slugs_to_ids(tmp_path):
    build_corpus(tmp_path)
    assert load(tmp_path).controls["FKE-PREV-1"].mitigates == ("FKE-SEC-1",)


def test_summary_is_the_first_section_only(tmp_path):
    build_corpus(tmp_path)
    s = load(tmp_path).risks["FKE-SEC-1"].summary
    assert "thing that can go wrong" in s
    assert "must not appear" not in s


def test_references_resolve_against_the_crosswalk(tmp_path):
    build_corpus(tmp_path)
    refs = load(tmp_path).controls["FKE-PREV-1"].references
    assert [r.title for r in refs] == ["Article 1 Record-keeping", "Article 2 Oversight"]
    assert all(r.resolved for r in refs)


def test_absent_submodule_is_a_state_not_a_crash(tmp_path):
    assert available(tmp_path) is False
    with pytest.raises(NotVendored):
        load(tmp_path)
    cov = assess(tmp_path)
    assert cov.vendored is False and len(cov) == 0
    assert gate(tmp_path, "g", "p").exit_code == 0


# ------------------------------------------------------------------ sources --
def test_a_catalogue_with_different_frontmatter_keys_parses(tmp_path, monkeypatch):
    """The proof that this is a catalogue reader, not a FINOS reader: a corpus
    that names every key differently and numbers its ids its own way."""
    odd = CatalogueSource(
        name="odd", title="Odd Library", path="ctl", prefix="ODD",
        id_template="{prefix}.{sequence}{type}",
        layout=Layout(risks="threats", controls="safeguards", references="xwalk"),
        frontmatter=Frontmatter(
            sequence="num", type="klass", title="name", status="state",
            mitigates="addresses", related_risks="see_also",
            related_controls="see_also", reference_suffix="__cites",
            slug_separator="."),
        risk_types={"T": "Threat"}, control_types={"S": "Safeguard"})
    monkeypatch.setattr("pf.air.sources.BUILTIN", (odd,))

    base = tmp_path / odd.path
    for d in ("threats", "safeguards", "xwalk"):
        (base / d).mkdir(parents=True)
    (base / "xwalk" / "reg.yml").write_text(
        'title: R\nentries:\n  a1:\n    title: "Rule 1"\n    url: "https://x.invalid"\n')
    (base / "threats" / "ri-1.leak.md").write_text(
        "---\nnum: 1\nklass: T\nname: Leak\nstate: Final\n---\n\n## What\n\nIt leaks.\n")
    (base / "safeguards" / "mi-4.plug.md").write_text(
        "---\nnum: 4\nklass: S\nname: Plug\nstate: Final\n"
        "addresses:\n  - ri-1\nreg__cites:\n  - a1\n---\n\n## Why\n\nIt plugs.\n")

    cat = load(tmp_path)
    assert set(cat.risks) == {"ODD.1T"}
    assert set(cat.controls) == {"ODD.4S"}
    ctl = cat.controls["ODD.4S"]
    assert ctl.mitigates == ("ODD.1T",)
    assert ctl.type_label == "Safeguard"
    assert [r.title for r in ctl.references] == ["Rule 1"]
    assert verify(tmp_path).ok


def test_two_catalogues_merge(tmp_path, monkeypatch):
    other = CatalogueSource(name="other", title="Other", path="catalogues/other",
                            prefix="OTH", layout=FAKE.layout,
                            risk_types=FAKE.risk_types, control_types=FAKE.control_types)
    monkeypatch.setattr("pf.air.sources.BUILTIN", (FAKE, other))
    build_corpus(tmp_path, src=FAKE)
    build_corpus(tmp_path, src=other)
    cat = load(tmp_path)
    assert set(cat.controls) == {"FKE-PREV-1", "OTH-PREV-1"}
    assert {s.name for s in cat.sources} == {"fake", "other"}


def test_a_prefix_collision_is_refused(monkeypatch):
    """Two catalogues claiming one prefix would make an air.yaml baseline
    ambiguous — a baseline that gates the wrong control is worse than one that
    fails to load."""
    clash = CatalogueSource(name="clash", title="Clash", path="x", prefix="FKE")
    monkeypatch.setattr("pf.air.sources.BUILTIN", (FAKE, clash))
    sources, errors = discover()
    assert "clash" not in sources
    assert any("already claimed" in e.error for e in errors)


def test_a_duplicate_name_is_refused(monkeypatch):
    twin = CatalogueSource(name="fake", title="Twin", path="y", prefix="TWN")
    monkeypatch.setattr("pf.air.sources.BUILTIN", (FAKE, twin))
    sources, errors = discover()
    assert any("duplicate catalogue name" in e.error for e in errors)
    assert sources["fake"].title == FAKE.title


def test_an_unrenderable_id_template_is_refused_at_construction():
    with pytest.raises(InvalidSource, match="id_template"):
        CatalogueSource(name="bad", title="Bad", path="z", prefix="BAD",
                        id_template="{prefix}-{nonsense}")


def test_a_source_needs_a_name_and_a_prefix():
    with pytest.raises(InvalidSource):
        CatalogueSource(name="", title="T", path="p", prefix="P")


# ------------------------------------------------------------------- verify --
def test_verify_passes_on_a_clean_corpus(tmp_path):
    build_corpus(tmp_path)
    rep = verify(tmp_path)
    assert rep.ok and rep.exit_code == 0


def test_verify_fails_on_a_dangling_citation(tmp_path):
    build_corpus(tmp_path, controls=[(1, "PREV", "X", [], ["art-1", "art-99"])])
    rep = verify(tmp_path)
    assert not rep.ok
    assert any(f.code == "citation.dangling_key" and "art-99" in f.detail
               for f in rep.failures)


def test_verify_fails_on_a_dangling_mitigates(tmp_path):
    build_corpus(tmp_path, controls=[(1, "PREV", "X", ["ri-404"], [])])
    rep = verify(tmp_path)
    assert any(f.code == "control.dangling_mitigates" for f in rep.failures)


def test_verify_warns_rather_than_fails_on_upstream_frontmatter_defect(tmp_path):
    """A citation shaped like a document slug is upstream's missing newline —
    a one-line fix in someone else's repo, not something to fail our merge on."""
    build_corpus(tmp_path, controls=[(1, "PREV", "X", [], ["art-1", "ri-2"])])
    rep = verify(tmp_path)
    assert rep.ok, "an upstream typo must not block the build"
    assert any(f.code == "corpus.frontmatter_malformed" for f in rep.warnings)


def test_verify_fails_on_an_unknown_type_letter(tmp_path):
    build_corpus(tmp_path, controls=[(1, "XXX", "X", [], [])])
    assert any(f.code == "control.unknown_type" for f in verify(tmp_path).failures)


# ---------------------------------------------------------------- resolution --
@pytest.mark.parametrize(
    "spec,expected",
    [
        ("pf.provenance.ledger:decision", True),        # module:symbol
        ("pf.tools.spec:Tool.gate_sections", True),     # module:Class.method
        ("pf.provenance.ledger:no_such_function", False),
        ("pf.ontology.validate:money-without-currency", True),   # a rule id
        ("pf.ontology.validate:no-such-rule", False),
        ("gate.yaml:denylist", True),                   # file:section
        ("gate.yaml:no_such_section", False),
        ("platform/hooks/pre_tool_use.py", True),       # plain path
        ("platform/hooks/nope.py", False),
        ("", False),
    ],
)
def test_artefact_resolution(spec, expected):
    assert _resolve_artefact(REPO, spec)[0] is expected


# ----------------------------------------------------------------- air.yaml --
def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text))


def test_project_baseline_unions_with_the_group(tmp_path):
    """A project may commit to more than its family, never to less — otherwise a
    group-level declaration is advisory and anyone can opt out by editing a file."""
    _write(tmp_path / "groups/g/air.yaml", "version: 1\nbaseline: [FKE-PREV-18]\n")
    _write(tmp_path / "groups/g/projects/p/air.yaml", "version: 1\nbaseline: [FKE-DET-21]\n")
    cfg = load_config(tmp_path, "g", "p")
    assert set(cfg.baseline) == {"FKE-PREV-18", "FKE-DET-21"}


def test_project_cannot_drop_a_group_control(tmp_path):
    _write(tmp_path / "groups/g/air.yaml", "version: 1\nbaseline: [FKE-PREV-18]\n")
    _write(tmp_path / "groups/g/projects/p/air.yaml", "version: 1\nbaseline: []\n")
    assert "FKE-PREV-18" in load_config(tmp_path, "g", "p").baseline


def test_acceptance_requires_a_reason(tmp_path):
    _write(tmp_path / "groups/g/air.yaml", """\
        version: 1
        accepted:
          - control: FKE-PREV-14
            owner: someone
        """)
    with pytest.raises(RegisterError, match="reason"):
        load_config(tmp_path, "g")


def test_acceptance_requires_an_owner(tmp_path):
    _write(tmp_path / "groups/g/air.yaml", """\
        version: 1
        accepted:
          - control: FKE-PREV-14
            reason: no warehouse yet
        """)
    with pytest.raises(RegisterError, match="owner"):
        load_config(tmp_path, "g")


def test_a_control_cannot_be_both_committed_and_accepted(tmp_path):
    build_corpus(tmp_path)
    _write(tmp_path / "groups/g/air.yaml", """\
        version: 1
        baseline: [FKE-PREV-1]
        accepted:
          - control: FKE-PREV-1
            reason: contradictory
            owner: someone
        """)
    problems = validate(load_config(tmp_path, "g"), load(tmp_path))
    assert any("cannot be both" in p for p in problems)


def test_baseline_naming_an_unknown_control_is_a_problem(tmp_path):
    build_corpus(tmp_path)
    _write(tmp_path / "groups/g/air.yaml", "version: 1\nbaseline: [FKE-PREV-999]\n")
    problems = validate(load_config(tmp_path, "g"), load(tmp_path))
    assert any("FKE-PREV-999" in p for p in problems)


def test_overdue_acceptance_is_flagged():
    assert Acceptance("FKE-PREV-14", "r", "o", "2020-01-01").overdue is True
    assert Acceptance("FKE-PREV-14", "r", "o", "2999-01-01").overdue is False
    assert Acceptance("FKE-PREV-14", "r", "o", "").overdue is False


# --------------------------------------------------------------- the verdict --
def _coverage_fixture(tmp_path, policy_yaml: str, src: CatalogueSource = FAKE):
    """A corpus plus a stand-in ontology whose policies we control."""
    build_corpus(tmp_path, src=src)

    class _Onto:
        def __init__(self, policies):
            self.policies = policies

        def policies_for_control(self, cid):
            return [p for p in self.policies
                    if cid.upper() in (c.upper() for c in p.controls)]

    import yaml as _yaml
    from pf.ontology.model import Policy

    doc = _yaml.safe_load(policy_yaml)
    policies = [
        Policy(id=p["id"], intent="", constraint="", enforced_by=p.get("enforced_by") or [],
               evidence=p.get("evidence") or [], controls=p.get("controls") or [])
        for p in doc["policies"]
    ]
    return _Onto(policies)


def test_a_control_no_policy_claims_fails(tmp_path, monkeypatch):
    onto = _coverage_fixture(tmp_path, "policies: [{id: other, controls: []}]")
    monkeypatch.setattr("pf.air.coverage._ontology", lambda *a: onto)
    v = assess(tmp_path).get("FKE-PREV-1")
    assert v.status == "fail" and "no policy" in v.check.evidence


def test_a_policy_with_no_enforced_by_fails(tmp_path, monkeypatch):
    """`Ontology.unenforced_policies()` — a control that exists only on paper."""
    onto = _coverage_fixture(
        tmp_path, "policies: [{id: p1, controls: [FKE-PREV-1], enforced_by: []}]")
    monkeypatch.setattr("pf.air.coverage._ontology", lambda *a: onto)
    v = assess(tmp_path).get("FKE-PREV-1")
    assert v.status == "fail" and "not enforced" in v.check.evidence


def test_a_policy_naming_a_missing_artefact_fails(tmp_path, monkeypatch):
    onto = _coverage_fixture(
        tmp_path,
        "policies: [{id: p1, controls: [FKE-PREV-1], "
        "enforced_by: ['pf.provenance.ledger:vanished']}]")
    monkeypatch.setattr("pf.air.coverage._ontology", lambda *a: onto)
    assert assess(tmp_path).get("FKE-PREV-1").status == "fail"


def test_a_resolving_artefact_with_no_evidence_is_unexercised(tmp_path, monkeypatch):
    onto = _coverage_fixture(
        tmp_path,
        "policies: [{id: p1, controls: [FKE-PREV-1], "
        "enforced_by: ['pf.provenance.ledger:decision'], "
        "evidence: ['pf provenance verify']}]")
    monkeypatch.setattr("pf.air.coverage._ontology", lambda *a: onto)
    v = assess(tmp_path).get("FKE-PREV-1")
    assert v.status == "unexercised", "no provenance/chain.jsonl in a tmp_path"


def test_a_resolving_artefact_with_evidence_passes(tmp_path, monkeypatch):
    onto = _coverage_fixture(
        tmp_path,
        "policies: [{id: p1, controls: [FKE-PREV-1], "
        "enforced_by: ['pf.provenance.ledger:decision'], "
        "evidence: ['pf provenance verify']}]")
    monkeypatch.setattr("pf.air.coverage._ontology", lambda *a: onto)
    (tmp_path / "provenance").mkdir()
    (tmp_path / "provenance" / "chain.jsonl").write_text("")
    assert assess(tmp_path).get("FKE-PREV-1").status == "pass"


def test_verdicts_are_derived_not_stored(tmp_path, monkeypatch):
    """The rule the whole module is built on: re-reading must re-decide."""
    onto = _coverage_fixture(
        tmp_path,
        "policies: [{id: p1, controls: [FKE-PREV-1], "
        "enforced_by: ['pf.provenance.ledger:decision'], "
        "evidence: ['pf provenance verify']}]")
    monkeypatch.setattr("pf.air.coverage._ontology", lambda *a: onto)
    (tmp_path / "provenance").mkdir()
    chain = tmp_path / "provenance" / "chain.jsonl"
    chain.write_text("")
    assert assess(tmp_path).get("FKE-PREV-1").status == "pass"
    chain.unlink()
    assert assess(tmp_path).get("FKE-PREV-1").status == "unexercised"


# ------------------------------------------------------------------- gating --
def _gate_fixture(tmp_path, monkeypatch, baseline: str, enforced_by: str):
    build_corpus(tmp_path)
    _write(tmp_path / "groups/g/air.yaml", f"version: 1\nbaseline: [{baseline}]\n")
    onto = _coverage_fixture(
        tmp_path,
        f"policies: [{{id: p1, controls: [FKE-PREV-1], enforced_by: {enforced_by}, "
        f"evidence: ['pf provenance verify']}}]")
    monkeypatch.setattr("pf.air.coverage._ontology", lambda *a: onto)
    return gate(tmp_path, "g", "p")


def test_gate_blocks_on_a_failing_committed_control(tmp_path, monkeypatch):
    res = _gate_fixture(tmp_path, monkeypatch, "FKE-PREV-1", "[]")
    assert res.exit_code == 1 and res.breaches


def test_gate_does_not_block_on_unexercised(tmp_path, monkeypatch):
    """Walling a project off over a ledger that has not been written yet is how a
    gate stops being run at all. Only `fail` closes it."""
    res = _gate_fixture(
        tmp_path, monkeypatch, "FKE-PREV-1", "['pf.provenance.ledger:decision']")
    assert res.exit_code == 0 and res.warned and not res.breaches


def test_gate_ignores_controls_outside_the_baseline(tmp_path, monkeypatch):
    build_corpus(tmp_path, controls=[
        (1, "PREV", "Claimed", ["ri-1"], []),
        (2, "DET", "Unclaimed", ["ri-1"], []),
    ])
    _write(tmp_path / "groups/g/air.yaml", "version: 1\nbaseline: [FKE-PREV-1]\n")
    onto = _coverage_fixture(
        tmp_path,
        "policies: [{id: p1, controls: [FKE-PREV-1], "
        "enforced_by: ['pf.provenance.ledger:decision'], evidence: []}]")
    monkeypatch.setattr("pf.air.coverage._ontology", lambda *a: onto)
    res = gate(tmp_path, "g", "p")
    assert res.exit_code == 0, "FKE-DET-2 fails but was never committed to"


# ----------------------------------------------------------------- register --
def test_register_states_provenance_even_with_no_attribution(tmp_path, monkeypatch):
    """A catalogue that requires no credit still gets its origin stated — a
    governance artefact with no provenance is one nobody can check."""
    build_corpus(tmp_path)
    _write(tmp_path / "groups/g/air.yaml", "version: 1\nbaseline: [FKE-PREV-1]\n")
    onto = _coverage_fixture(tmp_path, "policies: [{id: p1, controls: []}]")
    monkeypatch.setattr("pf.air.coverage._ontology", lambda *a: onto)
    from pf.air.register import NO_ATTRIBUTION
    assert NO_ATTRIBUTION in render_register(tmp_path, "g", "p")


def test_register_carries_every_source_attribution(tmp_path, monkeypatch):
    """The credit line comes from the sources actually loaded, not a template —
    so swapping the catalogue takes its obligation with it."""
    credited = CatalogueSource(
        name="credited", title="Credited Library", path="catalogues/credited",
        prefix="CRD", licence="CC-BY-4.0",
        attribution="Derived from the Credited Library, CC BY 4.0. Changes were made.",
        layout=FAKE.layout)
    monkeypatch.setattr("pf.air.sources.BUILTIN", (credited,))
    build_corpus(tmp_path, src=credited)
    _write(tmp_path / "groups/g/air.yaml", "version: 1\n")
    onto = _coverage_fixture(tmp_path, "policies: [{id: p1, controls: []}]", src=credited)
    monkeypatch.setattr("pf.air.coverage._ontology", lambda *a: onto)
    text = render_register(tmp_path, "g", "p")
    assert credited.attribution in text


def test_register_refuses_without_the_catalogue(tmp_path):
    with pytest.raises(RegisterError):
        render_register(tmp_path, "g", "p")


# --------------------------------------------------- the corpus we actually pin --
requires_corpus = pytest.mark.skipif(
    not available(REPO), reason="vendor/ai-governance-framework not checked out"
)


@requires_corpus
def test_the_pinned_corpus_honours_its_contract(real_catalogues):
    """Contract, not contents: no assertion here breaks when upstream adds a
    control, and every one breaks when a pin bump corrupts a cross-reference."""
    rep = verify(REPO)
    assert rep.ok, [f.detail for f in rep.failures]
    assert rep.risks and rep.controls and rep.regimes


@requires_corpus
def test_every_mapped_control_exists_in_the_pinned_catalogue(real_catalogues):
    """The mapping in policy.yaml must not name a control the pin does not have —
    this is the check that fires when a bump renames one."""
    from pf.ontology.model import load_ontology

    known = set(load(REPO).controls)
    unknown = [c for c in load_ontology().mapped_controls() if c not in known]
    assert not unknown, f"policy.yaml maps controls absent from the catalogue: {unknown}"


@requires_corpus
def test_declared_baselines_name_real_controls(real_catalogues):
    """Every group's air.yaml must survive a pin bump, or its gate silently
    stops checking the control it thinks it checks."""
    cat = load(REPO)
    for air in sorted((REPO / "groups").glob("*/air.yaml")):
        cfg = load_config(REPO, air.parent.name)
        problems = validate(cfg, cat)
        assert not problems, f"{air.relative_to(REPO)}: {problems}"
