"""Tests for onboarding an external repository.

The failures worth pinning are the silent ones. A model landing in the wrong
layer changes what the semantic layer reasons about. A capability judged
"already present" is a capability the project never gets. A dependency edge read
backwards produces a Dagster graph that runs in the wrong order and still looks
right.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import yaml
from pf.onboard.audit import audit
from pf.onboard.orchestrator import parse, render
from pf.onboard.run import _merge_dbt_project, _merge_packages, plan
from pf.onboard.survey import survey


def _repo(tmp_path: Path, dag: str = "", *, layers=("staging", "marts"),
          workflows: bool = False) -> Path:
    root = tmp_path / "src_repo"
    (root / "models").mkdir(parents=True)
    (root / "dbt_project.yml").write_text("name: 'incoming'\nversion: '1.0.0'\n", encoding="utf-8")
    for layer in layers:
        (root / "models" / layer).mkdir(parents=True, exist_ok=True)
        (root / "models" / layer / f"m_{layer}.sql").write_text("select 1", encoding="utf-8")
    if dag:
        (root / "dags").mkdir(exist_ok=True)
        (root / "dags" / "pipeline.py").write_text(textwrap.dedent(dag), encoding="utf-8")
    if workflows:
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    return root


# ---------------------------------------------------------------- survey ----
def test_layer_families_are_mapped(tmp_path: Path) -> None:
    """bronze/silver/gold and staging/intermediate/marts both have to land in
    this platform's three layers, or `pf gen-staging` and the metric layer
    reason about the wrong models."""
    root = _repo(tmp_path, layers=("bronze", "silver", "gold"))
    s = survey(root)
    assert s.layer_mapping == {"bronze": "staging", "silver": "marts", "gold": "marts"}
    assert len(s.models["marts"]) == 2


def test_an_unknown_layer_is_kept_and_reported(tmp_path: Path) -> None:
    """Dropping it would lose models silently; guessing a layer would put them
    somewhere the semantic layer then trusts."""
    root = _repo(tmp_path, layers=("staging", "reporting"))
    s = survey(root)
    assert "reporting" in s.unmapped_layers
    assert s.model_count == 2


def test_orchestrators_are_detected_by_import_not_by_directory(tmp_path: Path) -> None:
    """A `dags/` directory is a convention; an airflow import is a fact."""
    root = _repo(tmp_path, "from airflow import DAG\n")
    assert survey(root).orchestrators == {"airflow"}

    plain = _repo(tmp_path / "other", "def main():\n    pass\n")
    assert survey(plain).orchestrators == set()


def test_a_dagster_repo_needs_no_orchestrator_migration(tmp_path: Path) -> None:
    root = _repo(tmp_path, "from dagster import asset\n")
    s = survey(root)
    assert s.orchestrators == {"dagster"}
    assert not s.needs_orchestrator_migration


def test_capability_detection_is_conservative(tmp_path: Path) -> None:
    """A false positive means we skip wiring ours in and the project ships
    without it, so presence must be the thing itself."""
    assert survey(_repo(tmp_path, workflows=True)).capabilities_present == {"github"}
    assert survey(_repo(tmp_path / "b")).capabilities_present == set()


# --------------------------------------------------------- orchestrator -----
AIRFLOW = """
    from airflow import DAG
    from airflow.operators.python import PythonOperator

    with DAG(dag_id="etl", schedule_interval="0 6 * * *") as dag:
        a = PythonOperator(task_id="extract")
        b = PythonOperator(task_id="load")
        c = PythonOperator(task_id="report")
        a >> b >> [c]
"""


def test_task_ids_and_chain_order_survive(tmp_path: Path) -> None:
    root = _repo(tmp_path, AIRFLOW)
    p = parse(root / "dags" / "pipeline.py")[0]
    assert p.name == "etl"
    assert p.schedule == "0 6 * * *"
    assert [t.name for t in p.tasks] == ["extract", "load", "report"]
    assert p.edges == [("extract", "load"), ("load", "report")]


def test_left_shift_is_normalised_to_run_order(tmp_path: Path) -> None:
    """`a << b` means b runs first. Reading it as `a then b` produces a graph
    that runs backwards and still looks plausible."""
    root = _repo(tmp_path, """
        from airflow import DAG
        from airflow.operators.python import PythonOperator
        a = PythonOperator(task_id="second")
        b = PythonOperator(task_id="first")
        a << b
    """)
    p = parse(root / "dags" / "pipeline.py")[0]
    assert p.edges == [("first", "second")]


def test_set_upstream_and_downstream_are_read(tmp_path: Path) -> None:
    root = _repo(tmp_path, """
        from airflow import DAG
        from airflow.operators.python import PythonOperator
        a = PythonOperator(task_id="one")
        b = PythonOperator(task_id="two")
        a.set_downstream(b)
    """)
    assert parse(root / "dags" / "pipeline.py")[0].edges == [("one", "two")]


def test_unparseable_source_is_reported_not_skipped(tmp_path: Path) -> None:
    root = _repo(tmp_path, "from airflow import DAG\nthis is not python(\n")
    p = parse(root / "dags" / "pipeline.py")[0]
    assert p.error and not p.tasks


def test_generated_assets_raise_rather_than_guess(tmp_path: Path) -> None:
    """The core honesty property. Translating a task body would produce code
    that compiles and is quietly wrong; a stub is obviously unfinished."""
    root = _repo(tmp_path, AIRFLOW)
    out = render(parse(root / "dags" / "pipeline.py"), "m")
    assert out.count("NotImplementedError") == 3
    assert 'deps=["extract"]' in out
    assert 'cron_schedule="0 6 * * *"' in out


def test_prefect_tasks_are_listed_without_invented_edges(tmp_path: Path) -> None:
    """Prefect orders work through ordinary calls, so there is no reliable static
    edge set. Inferring one from call order is wrong the moment anything is
    conditional."""
    root = _repo(tmp_path, """
        from prefect import flow, task

        @task
        def pull(): ...

        @task
        def push(): ...

        @flow
        def nightly():
            push(pull())
    """)
    p = parse(root / "dags" / "pipeline.py")[0]
    assert p.framework == "prefect"
    assert {t.name for t in p.tasks} == {"pull", "push"}
    assert p.edges == []


# ------------------------------------------------------------------ plan ----
def test_plan_adds_only_the_capabilities_the_source_lacks(tmp_path: Path) -> None:
    root = _repo(tmp_path, workflows=True)
    p = plan(tmp_path, "g", "proj", root)
    assert "github" not in p.missing_capabilities
    assert "evidence" in p.missing_capabilities


def test_plan_reports_a_foreign_warehouse(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "profiles.yml").write_text("x:\n  outputs:\n    prod:\n      type: snowflake\n", encoding="utf-8")
    p = plan(tmp_path, "g", "proj", root)
    risk = next(r for r in p.risks if r.kind == "warehouse-foreign")
    assert "snowflake" in risk.detail
    # A foreign profile on its own is not a blocker; whether the *SQL* survives
    # is a separate finding, and conflating them cries wolf on every import.
    assert risk.severity == "note"


def test_the_checklist_names_the_work_no_tool_can_infer(tmp_path: Path) -> None:
    """A project that is present but unannotated contributes nothing to the
    graph, the metrics or the gate — and `validate_project` only warns."""
    p = plan(tmp_path, "g", "proj", _repo(tmp_path))
    assert any("annotations" in c for c in p.checklist)


def test_our_package_pin_wins_a_conflict(tmp_path: Path) -> None:
    """Ours is pinned against the dbt version this platform is tested with;
    taking the incoming pin could break every sister sharing the runtime."""
    src = tmp_path / "in.yml"
    src.write_text("packages:\n  - package: dbt-labs/dbt_utils\n    version: 0.9.0\n"
                   "  - package: other/pkg\n    version: 1.0.0\n", encoding="utf-8")
    dst = tmp_path / "out.yml"
    dst.write_text("packages:\n  - package: dbt-labs/dbt_utils\n    version: 1.1.1\n", encoding="utf-8")

    _merge_packages(src, dst)
    import yaml
    pkgs = yaml.safe_load(dst.read_text(encoding="utf-8"))["packages"]
    versions = {p["package"]: p["version"] for p in pkgs}
    assert versions["dbt-labs/dbt_utils"] == "1.1.1"
    assert versions["other/pkg"] == "1.0.0"


# ------------------------------------------------- config-driven layout ----
def test_path_keys_are_read_from_the_source_config(tmp_path: Path) -> None:
    """A project that keeps tests in `data-tests/` still has real tests.
    Assuming dbt's defaults finds an empty directory, reports zero, and imports
    the project stripped of its tests without saying so."""
    root = _repo(tmp_path)
    (root / "dbt_project.yml").write_text(
        "name: 'incoming'\n"
        'test-paths: ["data-tests"]\n'
        'snapshot-paths: ["snaps"]\n'
        'analysis-paths: ["explorations"]\n', encoding="utf-8")
    for d, stem in (("data-tests", "t"), ("snaps", "s"), ("explorations", "a")):
        (root / d).mkdir()
        (root / d / f"{stem}.sql").write_text("select 1", encoding="utf-8")

    s = survey(root)
    assert len(s.tests) == 1
    assert len(s.snapshots) == 1
    assert len(s.analyses) == 1


def test_build_output_is_not_imported(tmp_path: Path) -> None:
    """`target-base/` is a checked-in tool artefact in some repos. Importing it
    ships a stale manifest that `pf check` later reads as if it were current."""
    root = _repo(tmp_path)
    (root / "target-base").mkdir()
    (root / "target-base" / "stale.sql").write_text("select 1", encoding="utf-8")
    assert not any("target-base" in str(f) for f in survey(root).sql_files())


# -------------------------------------------------------------- conflict ----
def test_a_reserved_macro_override_is_detected(tmp_path: Path) -> None:
    """`generate_schema_name` decides where every model lands. The common
    override collapses staging and marts into one schema on non-prod targets,
    which breaks layer separation with no error anywhere."""
    root = _repo(tmp_path)
    (root / "macros").mkdir()
    (root / "macros" / "generate_schema_name.sql").write_text("{% macro x() %}{% endmacro %}", encoding="utf-8")
    (root / "macros" / "helper.sql").write_text("{% macro h() %}{% endmacro %}", encoding="utf-8")

    s = survey(root)
    assert set(s.reserved_macros) == {"generate_schema_name"}

    risk = next(r for r in audit(s) if r.kind == "reserved-macro")
    assert risk.severity == "blocks"

    p = plan(tmp_path, "g", "proj", root)
    macros = next(a for a in p.actions if a.kind == "macros")
    assert macros.count == 1, "the reserved macro should not be imported"


def test_duplicate_model_names_are_fatal(tmp_path: Path) -> None:
    """dbt resolves models by bare name regardless of directory."""
    root = _repo(tmp_path, layers=("staging", "marts"))
    (root / "models" / "marts" / "dupe.sql").write_text("select 1", encoding="utf-8")
    (root / "models" / "staging" / "dupe.sql").write_text("select 1", encoding="utf-8")
    risk = next(r for r in audit(survey(root)) if r.kind == "name-collision")
    assert risk.severity == "blocks" and "dupe" in risk.detail


# -------------------------------------------------------------- packages ----
def test_package_usage_and_pinning_are_reported(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "packages.yml").write_text(
        "packages:\n"
        "  - package: dbt-labs/dbt_utils\n"
        "    version: 1.3.3\n"
        '  - git: "https://github.com/dbt-labs/dbt-audit-helper.git"\n'
        "    revision: main\n", encoding="utf-8")
    (root / "models" / "marts" / "m_marts.sql").write_text(
        "select {{ dbt_utils.generate_surrogate_key(['a']) }}", encoding="utf-8")

    s = survey(root)
    assert s.package_usage["dbt-labs/dbt_utils"] == 1
    assert s.package_usage["https://github.com/dbt-labs/dbt-audit-helper.git"] == 0
    assert s.unpinned_packages

    kinds = {r.kind for r in audit(s)}
    assert {"package-unused", "package-unpinned"} <= kinds


def test_a_short_package_namespace_does_not_match_prose(tmp_path: Path) -> None:
    """Stripping `dbt_` off `dbt_date` leaves `date`, which matches every YAML
    description ending in the word — and inflates usage into the dozens."""
    root = _repo(tmp_path)
    (root / "packages.yml").write_text(
        "packages:\n  - package: godatadriven/dbt_date\n    version: 0.17.2\n", encoding="utf-8")
    (root / "models" / "marts" / "schema.yml").write_text(
        "models:\n  - name: m_marts\n    description: One row per order date.\n", encoding="utf-8")
    assert survey(root).package_usage["godatadriven/dbt_date"] == 0


# --------------------------------------------------------- config merge ----
def _scaffolded(tmp_path: Path) -> Path:
    target = tmp_path / "transform" / "dbt_project.yml"
    target.parent.mkdir(parents=True)
    target.write_text(yaml.safe_dump({
        "name": "ours", "profile": "ours",
        "model-paths": ["models"],
        "models": {"ours": {"staging": {"+materialized": "view"}}},
    }, sort_keys=False), encoding="utf-8")
    return target


def test_the_source_config_block_is_rekeyed_and_kept(tmp_path: Path) -> None:
    """The block is keyed by the *source* project name. Copied across as-is dbt
    ignores it entirely, silently dropping every tag and materialisation the
    project was written with."""
    root = _repo(tmp_path)
    (root / "dbt_project.yml").write_text(yaml.safe_dump({
        "name": "incoming",
        "vars": {"load_source_data": False},
        "models": {"incoming": {"marts": {"+tags": ["domain:finance"]}}},
    }, sort_keys=False), encoding="utf-8")
    target = _scaffolded(tmp_path)

    _merge_dbt_project(survey(root), target)
    merged = yaml.safe_load(target.read_text(encoding="utf-8"))

    assert merged["models"]["ours"]["marts"]["+tags"] == ["domain:finance"]
    assert "incoming" not in merged["models"]
    assert merged["vars"]["load_source_data"] is False
    # Identity stays ours: a project is defined by where it lives here.
    assert merged["name"] == "ours" and merged["profile"] == "ours"


def test_platform_settings_win_a_conflict(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "dbt_project.yml").write_text(yaml.safe_dump({
        "name": "incoming",
        "models": {"incoming": {"staging": {"+materialized": "table"}}},
    }, sort_keys=False), encoding="utf-8")
    target = _scaffolded(tmp_path)
    _merge_dbt_project(survey(root), target)
    merged = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert merged["models"]["ours"]["staging"]["+materialized"] == "view"


def test_the_dialect_toolkit_path_is_added_once(tmp_path: Path) -> None:
    """Re-asserted on merge so a project onboarded over an older scaffold still
    reaches the portable macros — but appended once, not once per run."""
    root = _repo(tmp_path)
    target = _scaffolded(tmp_path)
    s = survey(root)
    _merge_dbt_project(s, target)
    _merge_dbt_project(s, target)
    paths = yaml.safe_load(target.read_text(encoding="utf-8"))["macro-paths"]
    assert paths.count("../../../../../platform/toolkits/dbt-snowflake/macros") == 1


# ------------------------------------------------------------ platform fit --
def _big_repo(tmp_path: Path, *, tags: bool) -> Path:
    root = _repo(tmp_path)
    if tags:
        (root / "dbt_project.yml").write_text(yaml.safe_dump({
            "name": "incoming",
            "models": {"incoming": {"marts": {"+tags": ["domain:finance"]}}},
        }, sort_keys=False), encoding="utf-8")
    for i in range(900):
        (root / "models" / "marts" / f"a_fairly_long_mart_model_name_{i}.sql").write_text("select 1", encoding="utf-8")
    return root


def test_scale_is_reported_as_density_not_budget(tmp_path: Path) -> None:
    """An earlier version claimed a 900-model project could not fit inside the
    card budget. It was wrong: `pf kg card` truncates every section at a fixed
    limit, so its output is bounded whatever the project size. The cost of scale
    is that the card describes 12 of 900 — density, not budget."""
    risk = next(r for r in audit(survey(_big_repo(tmp_path, tags=True)))
                if r.kind == "card-density")
    assert not risk.blocking
    assert "rolls up" in risk.detail


def test_a_large_untagged_project_is_worth_a_decision(tmp_path: Path) -> None:
    """With no `domain:`/`type:` tags the card can only say how many models were
    omitted, not what they are."""
    risk = next(r for r in audit(survey(_big_repo(tmp_path, tags=False)))
                if r.kind == "card-density")
    assert risk.severity == "decide"
    assert "no tags" in risk.detail


def test_a_small_project_raises_no_scale_findings(tmp_path: Path) -> None:
    kinds = {r.kind for r in audit(survey(_repo(tmp_path)))}
    assert "card-density" not in kinds
    assert "gate-maxfiles" not in kinds


def test_blocking_findings_are_separated_from_advisory_ones(tmp_path: Path) -> None:
    p = plan(tmp_path, "g", "proj", _repo(tmp_path))
    assert all(r.severity in {"blocks", "decide", "note"} for r in p.risks)
    assert p.blocking == [r for r in p.risks if r.severity == "blocks"]


def test_config_directory_keys_follow_the_models_to_their_new_layer(tmp_path: Path) -> None:
    """The models were re-filed on the way in — `bronze/` became `staging/`. A
    config block still keyed `bronze` configures a directory that no longer
    exists, which dbt accepts in silence while every tag stops applying."""
    root = _repo(tmp_path, layers=("bronze", "gold"))
    (root / "dbt_project.yml").write_text(yaml.safe_dump({
        "name": "incoming",
        "models": {"incoming": {
            "bronze": {"+tags": ["layer:staging"]},
            "gold": {"+tags": ["domain:finance"]},
        }},
    }, sort_keys=False), encoding="utf-8")
    target = _scaffolded(tmp_path)

    _merge_dbt_project(survey(root), target)
    block = yaml.safe_load(target.read_text(encoding="utf-8"))["models"]["ours"]

    assert block["staging"]["+tags"] == ["layer:staging"]
    assert block["marts"]["+tags"] == ["domain:finance"]
    assert "bronze" not in block and "gold" not in block


def test_two_source_layers_collapsing_onto_one_are_merged(tmp_path: Path) -> None:
    """`intermediate/` and `marts/` both land in marts/, so their config has to
    merge rather than one silently overwriting the other."""
    root = _repo(tmp_path, layers=("intermediate", "marts"))
    (root / "dbt_project.yml").write_text(yaml.safe_dump({
        "name": "incoming",
        "models": {"incoming": {
            "intermediate": {"+tags": ["layer:intermediate"]},
            "marts": {"+materialized": "table"},
        }},
    }, sort_keys=False), encoding="utf-8")
    target = _scaffolded(tmp_path)

    _merge_dbt_project(survey(root), target)
    marts = yaml.safe_load(target.read_text(encoding="utf-8"))["models"]["ours"]["marts"]
    assert marts["+tags"] == ["layer:intermediate"]
    assert marts["+materialized"] == "table"


def test_source_path_keys_are_not_carried_into_our_config(tmp_path: Path) -> None:
    """They are read so nothing is missed, then everything is copied into this
    platform's layout. Carrying `data-tests` would leave the config naming a
    directory the files were moved out of."""
    root = _repo(tmp_path)
    (root / "dbt_project.yml").write_text(
        "name: 'incoming'\ntest-paths: [\"data-tests\"]\n", encoding="utf-8")
    (root / "data-tests").mkdir()
    (root / "data-tests" / "t.sql").write_text("select 1", encoding="utf-8")
    target = _scaffolded(tmp_path)

    s = survey(root)
    assert len(s.tests) == 1, "still read from the source"
    _merge_dbt_project(s, target)
    assert "data-tests" not in target.read_text(encoding="utf-8")


def test_an_unpinned_unused_package_is_dropped_not_merged(tmp_path: Path) -> None:
    """Either condition alone is only worth reporting. Together they mean a
    dependency that makes every build resolve differently and buys nothing."""
    root = _repo(tmp_path)
    (root / "packages.yml").write_text(
        "packages:\n"
        '  - git: "https://github.com/dbt-labs/dbt-audit-helper.git"\n'
        "    revision: main\n", encoding="utf-8")
    target = tmp_path / "transform" / "packages.yml"
    target.parent.mkdir(parents=True)
    target.write_text("packages: []\n", encoding="utf-8")

    note = _merge_packages(root / "packages.yml", target, survey(root))
    assert "dropped 1 unpinned and unused" in note
    assert "audit-helper" not in target.read_text(encoding="utf-8")


def test_an_unpinned_but_used_package_is_kept(tmp_path: Path) -> None:
    """The namespace is guessed, so usage is the check that stops a heuristic
    from removing a real dependency."""
    root = _repo(tmp_path)
    (root / "packages.yml").write_text(
        "packages:\n"
        '  - git: "https://github.com/dbt-labs/dbt-audit-helper.git"\n'
        "    revision: main\n", encoding="utf-8")
    (root / "models" / "marts" / "m_marts.sql").write_text(
        "{{ audit_helper.compare_relations() }}", encoding="utf-8")
    target = tmp_path / "transform" / "packages.yml"
    target.parent.mkdir(parents=True)
    target.write_text("packages: []\n", encoding="utf-8")

    assert "+1 package" in _merge_packages(root / "packages.yml", target, survey(root))


def test_a_pinned_unused_package_is_kept(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "packages.yml").write_text(
        "packages:\n  - package: dbt-labs/dbt_utils\n    version: 1.3.3\n", encoding="utf-8")
    target = tmp_path / "transform" / "packages.yml"
    target.parent.mkdir(parents=True)
    target.write_text("packages: []\n", encoding="utf-8")

    assert "+1 package" in _merge_packages(root / "packages.yml", target, survey(root))
