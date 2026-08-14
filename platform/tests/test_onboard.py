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

from pf.onboard.orchestrator import parse, render
from pf.onboard.run import _merge_packages, plan
from pf.onboard.survey import survey


def _repo(tmp_path: Path, dag: str = "", *, layers=("staging", "marts"),
          workflows: bool = False) -> Path:
    root = tmp_path / "src_repo"
    (root / "models").mkdir(parents=True)
    (root / "dbt_project.yml").write_text("name: 'incoming'\nversion: '1.0.0'\n")
    for layer in layers:
        (root / "models" / layer).mkdir(parents=True, exist_ok=True)
        (root / "models" / layer / f"m_{layer}.sql").write_text("select 1")
    if dag:
        (root / "dags").mkdir(exist_ok=True)
        (root / "dags" / "pipeline.py").write_text(textwrap.dedent(dag))
    if workflows:
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / ".github" / "workflows" / "ci.yml").write_text("name: ci\n")
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


def test_plan_warns_about_a_foreign_warehouse(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "profiles.yml").write_text("x:\n  outputs:\n    prod:\n      type: snowflake\n")
    p = plan(tmp_path, "g", "proj", root)
    assert any("snowflake" in w for w in p.warnings)


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
                   "  - package: other/pkg\n    version: 1.0.0\n")
    dst = tmp_path / "out.yml"
    dst.write_text("packages:\n  - package: dbt-labs/dbt_utils\n    version: 1.1.1\n")

    _merge_packages(src, dst)
    import yaml
    pkgs = yaml.safe_load(dst.read_text())["packages"]
    versions = {p["package"]: p["version"] for p in pkgs}
    assert versions["dbt-labs/dbt_utils"] == "1.1.1"
    assert versions["other/pkg"] == "1.0.0"
