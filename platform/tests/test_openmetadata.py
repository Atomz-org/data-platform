"""The OpenMetadata projection, checked against the vendored schemas.

`pf.projections.openmetadata` builds payloads for a server nobody runs in CI, so
"it works" cannot mean "the server accepted it". What it can mean is that every
payload conforms to the same JSON Schema the server validates against — the one
pinned in `vendor/openmetadata-standards`. If upstream adds a required field,
this fails here, at the pin bump, instead of at 3am against a live catalogue.

That is the `schema` coupling kind in the vendor registry, and it is the reason
the standards repo is pinned separately from the product.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pf.ontology.model import load_ontology
from pf.projections.openmetadata import (
    GLOSSARY_NAME,
    ROLE_CLASSIFICATION,
    _om_name,
    build_all,
    build_metrics,
)

SCHEMA_ROOT = (Path(__file__).resolve().parents[2]
               / "vendor" / "openmetadata-standards" / "schemas")

requires_schemas = pytest.mark.skipif(
    not SCHEMA_ROOT.is_dir(),
    reason="vendor/openmetadata-standards not checked out (git submodule update --init)")


#: Every vendored schema carries `$id: https://open-metadata.org/schema/<path>`,
#: so relative `$ref`s resolve into that namespace. Rather than rewriting the
#: identifiers — which would mean validating against something subtly not what
#: upstream publishes — the namespace is mapped back onto the checked-out tree.
_NS = "https://open-metadata.org/schema/"


def _load(path: Path):
    from referencing import Resource
    from referencing.jsonschema import DRAFT7

    return Resource(contents=json.loads(path.read_text()), specification=DRAFT7)


def _validator(rel: str):
    """A validator for one create-API schema, resolving $refs off the local tree.

    Without a working retriever every `$ref` is unresolvable and the payload
    passes trivially — a test that cannot fail is worse than no test, which is
    what `test_a_missing_required_field_actually_fails` exists to catch.
    """
    from jsonschema import Draft7Validator
    from referencing import Registry

    def retrieve(uri: str):
        if not uri.startswith(_NS):
            raise FileNotFoundError(f"unexpected schema reference: {uri}")
        return _load(SCHEMA_ROOT / uri[len(_NS):])

    root = _load(SCHEMA_ROOT / rel)
    registry = Registry(retrieve=retrieve)  # type: ignore[call-arg]
    return Draft7Validator(root.contents, registry=registry)


@pytest.fixture(scope="module")
def payload() -> dict[str, Any]:
    return build_all(load_ontology(), metrics=[
        {"name": "net_revenue", "label": "Net revenue",
         "description": "Revenue after refunds.", "expression": "sum(net_amount)"},
    ])


# --------------------------------------------------------------- conformance --
@requires_schemas
def test_the_glossary_conforms(payload: dict[str, Any]) -> None:
    _validator("api/data/createGlossary.json").validate(payload["glossary"])


@requires_schemas
def test_every_glossary_term_conforms(payload: dict[str, Any]) -> None:
    v = _validator("api/data/createGlossaryTerm.json")
    assert payload["glossary_terms"], "the ontology produced no terms"
    for term in payload["glossary_terms"]:
        v.validate(term)


@requires_schemas
def test_the_classification_and_every_tag_conform(payload: dict[str, Any]) -> None:
    _validator("api/classification/createClassification.json").validate(
        payload["classification"])
    v = _validator("api/classification/createTag.json")
    assert payload["tags"], "the ontology produced no role tags"
    for tag in payload["tags"]:
        v.validate(tag)


@requires_schemas
def test_every_metric_conforms(payload: dict[str, Any]) -> None:
    v = _validator("api/data/createMetric.json")
    for metric in payload["metrics"]:
        v.validate(metric)


@requires_schemas
def test_a_missing_required_field_actually_fails(payload: dict[str, Any]) -> None:
    """Proves the validator is wired to the real schema.

    `description` is required on a glossary. If $ref resolution were silently
    broken, every payload above would pass no matter what it contained.
    """
    from jsonschema import ValidationError

    broken = {k: v for k, v in payload["glossary"].items() if k != "description"}
    with pytest.raises(ValidationError):
        _validator("api/data/createGlossary.json").validate(broken)


# -------------------------------------------------------------------- mapping --
def test_names_never_contain_the_entity_link_separator() -> None:
    """`::` separates fields in OpenMetadata's entityLink grammar."""
    assert _om_name("a::b") == "a_b"
    assert _om_name("") == "unnamed"
    assert len(_om_name("x" * 400)) == 256


def test_pii_roles_also_carry_openmetadatas_own_sensitive_tag() -> None:
    """Publishing only our vocabulary would hide PII from every built-in policy."""
    onto = load_ontology()
    labels = build_all(onto)["column_tag_labels"]
    pii = onto.pii_roles()
    assert pii, "the shipped ontology declares no PII roles"
    for role in pii:
        fqns = {lbl["tagFQN"] for lbl in labels[role]}
        assert "PII.Sensitive" in fqns
        assert f"{ROLE_CLASSIFICATION}.{role}" in fqns
    for role in set(labels) - pii:
        assert "PII.Sensitive" not in {lbl["tagFQN"] for lbl in labels[role]}


def test_the_class_hierarchy_survives_the_projection() -> None:
    onto = load_ontology()
    terms = {t["name"]: t for t in build_all(onto)["glossary_terms"]}
    for name, cls in onto.classes.items():
        if cls.parent:
            assert terms[name]["parent"] == f"{_om_name(GLOSSARY_NAME)}.{cls.parent}"


def test_an_undocumented_concept_says_so_rather_than_shipping_a_blank() -> None:
    metrics = build_metrics([{"name": "m"}])
    assert "no description" not in metrics[0]["description"]
    assert metrics[0]["description"].strip()


def test_a_metric_without_a_name_is_dropped_not_emitted_unnamed() -> None:
    assert build_metrics([{"description": "orphan"}]) == []


# ----------------------------------------------------------------- the tool --
def test_the_workflow_is_portable_not_machine_local(tmp_path: Path) -> None:
    """A committed file with an absolute home directory works on one machine."""
    from pf.tools.openmetadata import build_workflow

    wf = build_workflow(tmp_path, "acme", "acme-us")
    src = wf["source"]["sourceConfig"]["config"]["dbtConfigSource"]
    for key in ("dbtManifestFilePath", "dbtCatalogFilePath", "dbtRunResultsFilePath"):
        assert not Path(src[key]).is_absolute(), f"{key} is absolute"
        assert str(tmp_path) not in src[key]


def test_the_token_is_referenced_never_embedded(monkeypatch: pytest.MonkeyPatch,
                                                tmp_path: Path) -> None:
    """The workflow is generated into a committed directory."""
    from pf.tools.openmetadata import ENV_TOKEN, build_workflow

    monkeypatch.setenv(ENV_TOKEN, "super-secret-value")
    wf = build_workflow(tmp_path, "acme", "acme-us")
    assert "super-secret-value" not in json.dumps(wf)
    security = wf["workflowConfig"]["openMetadataServerConfig"]["securityConfig"]
    assert security["jwtToken"] == f"${{{ENV_TOKEN}}}"


def test_the_service_name_keeps_sisters_apart() -> None:
    """Sisters have identically named marts by design — that is conformance."""
    from pf.tools.openmetadata import settings

    us = settings(None, "acme", "acme-us")["service_name"]
    eu = settings(None, "acme", "acme-eu")["service_name"]
    assert us != eu
    assert "-" not in us


def test_config_beats_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    from pf.tools.openmetadata import ENV_HOST, settings

    monkeypatch.setenv(ENV_HOST, "http://from-env:8585")
    assert settings(None, "g", "p")["host_port"] == "http://from-env:8585"
    assert settings({"host_port": "http://from-config:8585/"},
                    "g", "p")["host_port"] == "http://from-config:8585"


def test_dbt_must_not_overwrite_the_glossarys_descriptions(tmp_path: Path) -> None:
    """The ontology is why a column is called personal data, not dbt's docs."""
    from pf.tools.openmetadata import build_workflow

    cfg = build_workflow(tmp_path, "g", "p")["source"]["sourceConfig"]["config"]
    assert cfg["dbtUpdateDescriptions"] is False


def test_bootstrap_skips_a_project_with_no_dbt(tmp_path: Path) -> None:
    from pf.tools.openmetadata import bootstrap_project

    r = bootstrap_project(tmp_path, "g", "p", tmp_path, {})
    assert r.status == "skipped"


def test_bootstrap_writes_the_artefacts_without_the_client(tmp_path: Path) -> None:
    """`offline_bootstrap`: scaffolding must not depend on who ran it."""
    from pf.tools.openmetadata import bootstrap_project, payload_path, workflow_path

    (tmp_path / "transform").mkdir()
    (tmp_path / "transform" / "dbt_project.yml").write_text("name: p\n")
    r = bootstrap_project(tmp_path, "acme", "acme-us", tmp_path, {})
    assert r.status == "ok"
    assert workflow_path(tmp_path).exists()
    assert payload_path(tmp_path).exists()


def test_the_tool_declares_offline_and_a_non_embeddable_surface() -> None:
    """Both are load-bearing; see the module docstring and Surface.embeddable.

    `offline`, not the `offline_bootstrap` this asserted before: the flag was
    widened to cover the Dagster hook as well as the scaffold one, because
    neither needs the `metadata` binary — the projections are local and
    publishing is REST — and gating only the bootstrap half left the container
    serving eight code locations with the catalogue asset silently absent.
    """
    from pf.tools.openmetadata import TOOL

    assert TOOL.offline is True
    assert TOOL.default_enabled is True
    assert TOOL.surface is not None and TOOL.surface.embeddable is False
