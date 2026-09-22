"""Creating a tenant from something other than a terminal.

`pf.scaffold.provision` exists so that the browser and the shell cannot produce
different projects from the same inputs. That guarantee is only worth anything
while these hold, and each of them is easy to lose without noticing:

  one code path            a capability registered tomorrow must reach a project
                             created from the UI on the same day it reaches one
                             created from the CLI, with nobody editing the UI

  refuse, never correct    the generator falls back to `b2b_saas` for a domain
                             it does not know. Behind a form that is a silent
                             wrong answer: the operator picks something, the
                             scaffold succeeds, and the ontology is not the one
                             they chose

  identity at creation     `new_group` writes an empty owner because the
                             template cannot know one. Every group in this repo
                             still has one, which is how `pf offboard` came to
                             have nobody to notify

  no actor, no write       same rule as the governance edits — a record whose
                             author can be blank says a tenant appeared and
                             nothing about who decided that
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from pf.scaffold import provision as sc


def _root(tmp_path: Path) -> Path:
    """A repository skeleton: the two marker directories and nothing else."""
    (tmp_path / "platform").mkdir(exist_ok=True)
    (tmp_path / "groups").mkdir(exist_ok=True)
    return tmp_path


def _manifest(root: Path, group: str) -> dict:
    return yaml.safe_load((root / "groups" / group / "group.yaml").read_text())


# ------------------------------------------------------------------ names --
@pytest.mark.parametrize(
    "name",
    [
        "Acme",  # a directory the module import will not match
        "acme_us",  # underscore: legal in Python, not in the dbt profile key
        "acme--us",  # doubled hyphen survives into the Dagster location name
        "-acme",
        "acme-",
        "",
    ],
)
def test_a_name_that_is_not_also_a_module_name_is_refused(name: str) -> None:
    """The failure from a bad name arrives late — at `dbt parse`, or at Dagster
    load — long after the files exist and the scaffold reported success."""
    with pytest.raises(sc.ProvisionError):
        sc.validate_name("project", name)


def test_the_rule_is_in_the_message_not_just_the_refusal() -> None:
    """An operator who has just been told 'invalid' still has to guess. The one
    thing that makes the message useful is an example of a name that works."""
    with pytest.raises(sc.ProvisionError, match="acme-us"):
        sc.validate_name("project", "Acme Corp")


def test_a_name_longer_than_the_limit_is_refused_with_both_numbers() -> None:
    with pytest.raises(sc.ProvisionError, match=f"{sc.NAME_MAX}"):
        sc.validate_name("group", "a" * (sc.NAME_MAX + 1))


# ------------------------------------------------------------------ group --
def test_the_identity_the_template_cannot_know_is_written_with_the_group(
    tmp_path: Path,
) -> None:
    """The whole reason this wraps `new_group` rather than calling it directly.

    The generator writes `display_name: ''` and an empty owner because those are
    per-tenant facts a template cannot hold. Recording them in the same call is
    the only moment the person who knows the answer is reliably present.
    """
    root = _root(tmp_path)

    sc.create_group(
        root,
        "northwind",
        "ecommerce",
        display_name="Northwind Traders",
        owner_team="data-eng",
        owner_contact="data@northwind.test",
        tier="critical",
    )

    m = _manifest(root, "northwind")
    assert m["display_name"] == "Northwind Traders"
    assert m["owner"] == {"team": "data-eng", "contact": "data@northwind.test"}
    assert m["tier"] == "critical"
    # Untouched by the amendment: a group is not live because someone filled in
    # a form. `pf group set-lifecycle` is the transition, and it is checked.
    assert m["lifecycle"] == "proposed"
    assert m["domain"] == "ecommerce"


def test_a_field_not_supplied_is_left_as_the_template_wrote_it(tmp_path: Path) -> None:
    """The amendment is a patch, not a rewrite. A caller that names only the
    display name must not blank the owner the template seeded."""
    root = _root(tmp_path)

    sc.create_group(root, "globex", "b2b_saas", display_name="Globex")

    m = _manifest(root, "globex")
    assert m["display_name"] == "Globex"
    assert m["owner"] == {"team": "", "contact": ""}
    assert m["tier"] == "standard"


def test_an_unknown_domain_is_refused_rather_than_defaulted(tmp_path: Path) -> None:
    """`new_group` falls back to `b2b_saas` for a domain it does not recognise.

    That is a reasonable default for a typed command and a silent wrong answer
    behind a form: the operator picks `retail`, the scaffold succeeds, and the
    ontology instance seeded is not the one they chose. Nothing tells them.
    """
    root = _root(tmp_path)

    with pytest.raises(sc.ProvisionError, match="unknown domain"):
        sc.create_group(root, "acme", "retail")

    assert not (root / "groups" / "acme").exists(), "a refused group left a directory"


def test_every_offered_domain_seeds_the_classes_it_advertises(tmp_path: Path) -> None:
    """`domains()` is what the picker renders. If it can name an archetype the
    generator seeds differently, the preview beside the picker is a lie."""
    root = _root(tmp_path)

    for i, (domain, classes) in enumerate(sorted(sc.domains().items())):
        result = sc.create_group(root, f"g{i}", domain)
        assert result.classes == classes
        inst = yaml.safe_load((root / "groups" / f"g{i}" / "ontology" / "instance.yaml").read_text())
        assert inst["classes"] == classes


def test_a_second_group_of_the_same_name_is_refused_with_the_recovery(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    sc.create_group(root, "acme", "b2b_saas")

    with pytest.raises(sc.ProvisionError, match="pf bootstrap acme"):
        sc.create_group(root, "acme", "b2b_saas")


# ---------------------------------------------------------- capability set --
def test_the_capability_set_is_defaults_plus_with_minus_without() -> None:
    """A project that has to be asked for its capabilities gets the ones whoever
    was asked remembered. The form is seeded from the defaults for that reason,
    so this rule has to be the CLI's rule and not a second one."""
    from pf.capabilities import defaults as registry_defaults

    base = {c.name for c in sc.resolve_capability_set()}
    assert base >= set(registry_defaults())

    added = {c.name for c in sc.resolve_capability_set(["snowflake"])}
    assert added == base | {"snowflake"}

    dropped = {c.name for c in sc.resolve_capability_set(without=["github"])}
    assert "github" not in dropped


def test_an_unknown_capability_names_what_is_available() -> None:
    with pytest.raises(sc.ProvisionError, match="unknown capability"):
        sc.resolve_capability_set(["teradata"])


# ---------------------------------------------------------------- project --
def test_a_blocked_scaffold_writes_nothing(tmp_path: Path) -> None:
    """`pf bootstrap` backfills what is missing but never removes what should
    not have been added, so a refusal that half-wrote is unrecoverable."""
    root = _root(tmp_path)

    with pytest.raises(sc.ProvisionError, match="does not exist"):
        sc.create_project(root, "nosuch", "nosuch-us", caps=[])

    assert not (root / "groups" / "nosuch").exists()


def test_a_bad_project_name_blocks_the_plan_rather_than_raising_at_apply(
    tmp_path: Path,
) -> None:
    """The plan is the surface the decision is made on. A name it accepts and
    the apply then rejects makes the preview worth less than trying it."""
    root = _root(tmp_path)
    sc.create_group(root, "acme", "b2b_saas")

    p = sc.plan_project(root, "acme", "Acme_US", caps=[])

    assert not p.ok
    assert any("Acme_US" in b for b in p.blockers)


def test_a_project_arrives_with_its_capabilities_and_its_ladder_run(
    tmp_path: Path,
) -> None:
    """The end-to-end guarantee, and the reason the UI does not assemble these
    steps itself: files, then capabilities, then the gate overlay derived from
    the capabilities that were actually applied, then the shared bootstrap."""
    root = _root(tmp_path)
    sc.create_group(root, "northwind", "ecommerce")
    caps = sc.resolve_capability_set(["snowflake"])

    r = sc.create_project(root, "northwind", "northwind-us", caps=caps)

    pdir = root / "groups" / "northwind" / "projects" / "northwind-us"
    assert (pdir / "transform" / "dbt_project.yml").is_file()
    assert "snowflake" in r.capabilities
    assert r.capability_files["snowflake"] > 0
    assert r.gate_rules_added > 0
    assert (root / "gate.capabilities.yaml").is_file()

    # Every step reported, not a single boolean: a project whose ladder half-ran
    # exists on disk and is not finished, and "created ✓" over a failed graph
    # build is the report that costs someone an afternoon.
    assert r.steps, "the bootstrap ladder did not run"
    assert {s.status for s in r.steps} <= {"ok", "created", "skipped", "failed"}
    assert [s.name for s in r.steps if s.status == "failed"] == []

    # The env a capability needs is reported, and does not block: the scaffold is
    # inert without credentials and `pf doctor` reports them later.
    assert "snowflake" in r.missing_env or not r.missing_env


# ------------------------------------------------------------ gate overlay --
def test_the_gate_overlay_is_appended_to_and_never_loosened(tmp_path: Path) -> None:
    """A capability may tighten the gate, never loosen it — and the hand-written
    `gate.yaml` is never round-tripped, because the dumper strips the comments
    where each rule's reason lives."""
    root = _root(tmp_path)
    path = root / "gate.capabilities.yaml"
    path.write_text(yaml.safe_dump({"deny": ["provenance/**"]}))

    first = sc.merge_gate_rules(root, {"deny": ["secrets/**"], "ask": ["dbt/**"]})
    second = sc.merge_gate_rules(root, {"deny": ["secrets/**"]})

    body = yaml.safe_load(path.read_text())
    assert body["deny"] == ["provenance/**", "secrets/**"], "an existing rule was lost"
    assert body["ask"] == ["dbt/**"]
    assert len(first) == 2
    assert second == [], "re-merging the same rule reported a change"


def test_merging_nothing_does_not_create_the_overlay(tmp_path: Path) -> None:
    """A project scaffolded with no capability must not leave an empty generated
    file that later reads as 'the gate was configured'."""
    root = _root(tmp_path)

    assert sc.merge_gate_rules(root, {}) == []
    assert not (root / "gate.capabilities.yaml").exists()


# -------------------------------------------------------------------- api --
@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """The control plane, pointed at a throwaway repository.

    Patched on `pf.ui.provision` rather than on `pf.obs`: the handlers call this
    module's `root_dir`, and patching the thing they actually call is what keeps
    the fixture honest if the indirection changes.
    """
    from pf.ui import provision as ui_provision

    root = _root(tmp_path)
    monkeypatch.setattr(ui_provision, "root_dir", lambda: root)

    from pf.ui.app import app

    client = TestClient(app)
    client.root = root  # type: ignore[attr-defined]
    return client


def test_a_write_without_an_actor_is_refused(client: TestClient) -> None:
    """Same rule as the governance edits. A tenant created by nobody records
    that something changed and nothing about who decided it."""
    for path, body in (
        ("/api/provision/group", {"group": "acme", "domain": "b2b_saas"}),
        ("/api/provision/project", {"group": "acme", "project": "acme-us"}),
    ):
        r = client.post(path, json=body)
        assert r.status_code == 400
        assert "actor" in r.json()["detail"]

    assert not (client.root / "groups" / "acme").exists()  # type: ignore[attr-defined]


def test_a_plan_writes_nothing(client: TestClient) -> None:
    """A dry run that leaves a directory behind is worse than no dry run,
    because the next apply then refuses on the mess it made."""
    root: Path = client.root  # type: ignore[attr-defined]

    assert client.post("/api/provision/group/plan", json={"group": "acme", "domain": "fintech"}).json()["ok"]
    client.post("/api/provision/project/plan", json={"group": "acme", "project": "acme-us"})

    assert list((root / "groups").iterdir()) == []


def test_the_group_plan_names_the_blocker_and_the_warning(client: TestClient) -> None:
    """The blockers are the point. A plan listing what would happen but not what
    would stop it is one you still have to try before you trust it."""
    body = client.post("/api/provision/group/plan", json={"group": "Acme Corp", "domain": "retail"}).json()

    assert not body["ok"]
    assert len(body["blockers"]) == 2, "name and domain should both be reported"
    # An absent owner is a warning, not a blocker: refusing here would make the
    # form stricter than the CLI for no safety gain.
    assert any("owner" in w for w in body["warnings"])


def test_the_options_call_names_nothing_of_its_own(client: TestClient) -> None:
    """The picker offers what the registries hold, asked at request time. A
    hardcoded list is how a form comes to offer a warehouse the scaffolder has
    never heard of — or to omit one that was added yesterday."""
    from pf.capabilities import CAPABILITIES
    from pf.groups import LIFECYCLE, TIERS
    from pf.runtime.targets import WAREHOUSES

    o = client.get("/api/provision/options").json()

    assert {d["name"] for d in o["domains"]} == set(sc.domains())
    assert {c["name"] for c in o["capabilities"]} == set(CAPABILITIES)
    assert set(o["warehouses"]) == set(WAREHOUSES)
    assert o["lifecycles"] == list(LIFECYCLE)
    assert o["tiers"] == list(TIERS)
    assert all(d["classes"] for d in o["domains"]), "a domain with no classes"


def test_creating_a_group_over_http_records_it_and_returns_what_was_written(
    client: TestClient,
) -> None:
    """The click has no PreToolUse hook over it, so the three provenance stages
    a shell command gets for free are written by the route or not at all."""
    from pf import provenance

    root: Path = client.root  # type: ignore[attr-defined]

    body = client.post(
        "/api/provision/group",
        json={
            "group": "northwind",
            "domain": "ecommerce",
            "display_name": "Northwind Traders",
            "owner_team": "data-eng",
            "actor": "sam@northwind.test",
            "reason": "new tenant",
        },
    ).json()

    assert body["file_count"] == len(body["files"]) > 0
    assert body["classes"] == sc.domains()["ecommerce"]
    assert _manifest(root, "northwind")["display_name"] == "Northwind Traders"

    recorded = provenance.actions(root)
    assert recorded, "the write left no provenance"
    stages = next(iter(recorded.values()))
    assert {"intent", "decision", "execution"} <= set(stages)
    assert "sam@northwind.test" in stages["intent"].payload["summary"]
    assert stages["execution"].payload["status"] == "ok"


def test_the_fleet_reads_node_counts_by_their_real_kind() -> None:
    """`NODE_KINDS` are capitalised. The lowercase guess reported nought models
    for a project with thirty-seven, so the labels are checked against the real
    tuple rather than against a copy of it that can drift."""
    from pf.kg.store import NODE_KINDS
    from pf.ui.provision import HEADLINE_KINDS, headline_counts

    assert set(HEADLINE_KINDS.values()) <= set(NODE_KINDS), (
        "the fleet table asks the graph for a kind it does not have"
    )
    assert headline_counts({"Model": 37, "Test": 25}) == {
        "models": 37, "sources": 0, "metrics": 0, "tests": 25,
    }


def test_an_ungraphed_project_reports_absence_not_zero(client: TestClient) -> None:
    """A green nought over a project nothing has measured is a clean bill of
    health nobody issued. `None` is what lets the table say 'not built'."""
    from pf.ui import provision as ui_provision

    root: Path = client.root  # type: ignore[attr-defined]
    pdir = root / "groups" / "acme" / "projects" / "acme-us"
    pdir.mkdir(parents=True)

    row = ui_provision._project_row(root, "acme", pdir)

    assert row["has_graph"] is False
    assert row["counts"] == {}
    assert row["models"] is None, "an unmeasured project reported a count"
    assert row["warehouse"] == ""


def test_the_fleet_surfaces_a_group_whose_manifest_will_not_load(
    client: TestClient,
) -> None:
    """The one case where the operator must see the group *and* the fault. A
    malformed manifest that drops the group from the list looks like an
    offboarded tenant."""
    root: Path = client.root  # type: ignore[attr-defined]
    (root / "groups" / "broken").mkdir(parents=True)
    (root / "groups" / "broken" / "group.yaml").write_text(
        "schema_version: 1\ngroup: broken\nbudget:\n  daily_tokens: -5\n"
    )

    body = client.get("/api/fleet").json()

    broken = next(g for g in body["groups"] if g["name"] == "broken")
    assert broken["error"], "a manifest that will not load was reported as fine"


def test_a_group_with_no_manifest_is_listed_as_unmanaged(client: TestClient) -> None:
    """A directory under `groups/` that predates `group.yaml` is still a tenant.
    Reported separately so it can be adopted rather than silently skipped."""
    root: Path = client.root  # type: ignore[attr-defined]
    (root / "groups" / "legacy" / "projects").mkdir(parents=True)

    body = client.get("/api/fleet").json()

    assert "legacy" in body["unmanaged"]
    assert any(g["name"] == "legacy" for g in body["groups"])


def test_creating_a_project_over_http_runs_the_whole_ladder(client: TestClient) -> None:
    """The route is thin, but the two things it owns are easy to get wrong: the
    `with` alias the form sends, and reporting a half-run ladder as success."""
    from pf import provenance

    root: Path = client.root  # type: ignore[attr-defined]
    client.post(
        "/api/provision/group",
        json={"group": "northwind", "domain": "ecommerce", "actor": "sam@northwind.test"},
    )

    r = client.post(
        "/api/provision/project",
        json={
            "group": "northwind", "project": "northwind-us",
            "with": ["snowflake"], "without": [],
            "actor": "sam@northwind.test", "reason": "US entity",
        },
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert "snowflake" in body["capabilities"], "the `with` alias did not bind"
    assert (root / "groups/northwind/projects/northwind-us/transform/dbt_project.yml").is_file()

    # Every step reported, and `ok` reflects them rather than the HTTP status.
    failed = [s for s in body["steps"] if s["status"] == "failed"]
    assert body["ok"] == (not failed)
    assert failed == [], f"bootstrap steps failed: {failed}"

    # Two tenants created, two actions in the chain, each one closed.
    recorded = provenance.actions(root)
    assert len(recorded) == 2
    for stages in recorded.values():
        assert {"intent", "decision", "execution"} <= set(stages)
        assert stages["execution"].payload["status"] == "ok"


def test_a_failed_scaffold_is_recorded_as_an_error_not_left_dangling(
    client: TestClient,
) -> None:
    """`provenance.action` writes an EXECUTION on the way out of a raising body.
    Without that the chain gains an intent nobody ever closed, and
    `pf provenance verify` reports it as dangling for ever."""
    from pf import provenance

    root: Path = client.root  # type: ignore[attr-defined]

    r = client.post(
        "/api/provision/project",
        json={"group": "nosuch", "project": "nosuch-us", "actor": "sam@example.test"},
    )

    assert r.status_code == 400
    assert "does not exist" in r.json()["detail"]
    assert provenance.dangling(root) == []
