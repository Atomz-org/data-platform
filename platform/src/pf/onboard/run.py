"""Plan and apply an onboarding.

Plan-then-apply, for the same reason the migrations in `dbt-migrate` are: this
writes a whole project, rewrites an orchestrator and merges dependency files, and
the moment to find out it mapped `intermediate/` somewhere unexpected is before
it happens rather than after.

The apply is not resumable and does not overwrite. `new_project` refuses an
existing project, which is deliberate — a half-onboarded project that gets
onboarded again on top of itself is worse than one that stops.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pf.capabilities import CAPABILITIES, apply as apply_capability, resolve
from pf.onboard.orchestrator import QUARANTINE, Pipeline, parse, render
from pf.onboard.survey import Survey, survey
from pf.scaffold.generator import new_project


@dataclass
class Action:
    kind: str
    detail: str
    count: int = 0


@dataclass
class Plan:
    group: str
    project: str
    source: Path
    survey: Survey
    pipelines: list[Pipeline] = field(default_factory=list)
    missing_capabilities: list[str] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checklist: list[str] = field(default_factory=list)


def resolve_source(source: str, workdir: Path) -> Path:
    """A local path, or a git URL cloned shallowly.

    Shallow because onboarding takes the tree, not the history — the project's
    history stays in its original repository, which remains the record of how it
    got that way.
    """
    p = Path(source).expanduser()
    if p.exists():
        return p.resolve()

    workdir.mkdir(parents=True, exist_ok=True)
    target = workdir / "source"
    if target.exists():
        shutil.rmtree(target)
    proc = subprocess.run(
        ["git", "clone", "--depth", "1", source, str(target)],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"could not clone {source}: {proc.stderr.strip()}")
    return target


def plan(root: Path, group: str, project: str, source: Path) -> Plan:
    """Work out everything that would happen, without doing any of it."""
    s = survey(source)
    p = Plan(group=group, project=project, source=source, survey=s)

    p.actions.append(Action("scaffold", f"pf new-project {group} {project}"))

    if s.dbt_project is None:
        p.warnings.append(
            "no dbt_project.yml found — models will not be imported, and the "
            "knowledge graph has nothing to build from")
    else:
        for layer, files in sorted(s.models.items()):
            p.actions.append(Action("models", f"transform/models/{layer}/", len(files)))
        if s.macros:
            p.actions.append(Action("macros", "transform/macros/", len(s.macros)))
        if s.seeds:
            p.actions.append(Action("seeds", "transform/seeds/", len(s.seeds)))
        if s.tests:
            p.actions.append(Action("tests", "transform/tests/", len(s.tests)))
        if s.packages:
            p.actions.append(Action("packages", "merge into transform/packages.yml"))

    for f in s.orchestration_files:
        p.pipelines += parse(f)
    if p.pipelines:
        tasks = sum(len(x.tasks) for x in p.pipelines)
        frameworks = ", ".join(sorted({x.framework for x in p.pipelines}))
        p.actions.append(Action(
            "orchestrator",
            f"{frameworks} -> dagster: {len(p.pipelines)} pipeline(s), "
            f"{tasks} task(s) as stubs; originals kept in {QUARANTINE}/",
            tasks))

    # Every capability we have that the source does not already solve for itself.
    p.missing_capabilities = sorted(set(CAPABILITIES) - s.capabilities_present)
    for name in p.missing_capabilities:
        p.actions.append(Action("capability", name))

    _add_warnings(p)
    _add_checklist(p)
    return p


def _add_warnings(p: Plan) -> None:
    s = p.survey
    if s.unmapped_layers:
        p.warnings.append(
            f"unrecognised model directories {sorted(s.unmapped_layers)} — placed "
            f"under marts/; move any that are really staging before `pf seed`")
    foreign = s.warehouses - {"duckdb", "motherduck"}
    if foreign:
        p.warnings.append(
            f"source targets {', '.join(sorted(foreign))}; this platform gives each "
            f"project its own DuckDB. Models using warehouse-specific SQL will need "
            f"porting — see the dbt-migrate toolkit")
    if s.ingestion - {"dlt"}:
        p.warnings.append(
            f"ingestion via {', '.join(sorted(s.ingestion - {'dlt'}))} is not "
            f"replaced; this platform expects annotated dlt sources")
    for pipeline in p.pipelines:
        if pipeline.error:
            p.warnings.append(f"{pipeline.source.name}: {pipeline.error}")
        elif not pipeline.tasks:
            p.warnings.append(
                f"{pipeline.source.name}: no tasks recovered — likely a dynamically "
                f"built graph; port it by hand")


def _add_checklist(p: Plan) -> None:
    """The semantic half. None of this is automatable, and all of it is required
    before the project is really onboarded rather than merely present."""
    p.checklist = [
        ("Annotate sources in contracts/annotations.yaml — this drives generated "
         "staging, currency normalisation and PII detection, and nothing works "
         "until it exists."),
        ("Declare `meta.grain` on every mart; the semantic layer owns aggregation "
         "policy and needs the grain to do it."),
        ('Declare foreign keys with links={"col": "SomeClass"} — `pf check` '
         "fails on an undeclared join."),
        (f"Confirm the incoming concepts exist in groups/{p.group}/ontology/"
         "instance.yaml, or add them."),
        "Run `pf check` until conformant, then `pf seed`.",
    ]
    if p.pipelines:
        tasks = sum(len(x.tasks) for x in p.pipelines)
        p.checklist.insert(0, (f"Port {tasks} orchestrator task bodies — every "
                               f"generated asset raises until you do."))


# ------------------------------------------------------------------- apply --
def apply(root: Path, p: Plan) -> list[str]:
    """Execute a plan. Returns a log of what was done."""
    log: list[str] = []
    pdir = root / "groups" / p.group / "projects" / p.project

    created = new_project(root, p.group, p.project)
    log.append(f"scaffolded {len(created)} file(s)")

    s = p.survey
    if s.dbt_project is not None:
        dbt_dir = s.dbt_project.parent
        for layer, files in sorted(s.models.items()):
            n = _copy_models(files, dbt_dir / "models", pdir / "transform" / "models" / layer)
            log.append(f"models -> {layer}/: {n}")
        for label, files, dest in (
            ("macros", s.macros, pdir / "transform" / "macros"),
            ("seeds", s.seeds, pdir / "transform" / "seeds"),
            ("tests", s.tests, pdir / "transform" / "tests"),
        ):
            if files:
                base = dbt_dir / label
                log.append(f"{label}: {_copy_models(files, base, dest)}")
        if s.packages:
            log.append(f"packages.yml: {_merge_packages(s.packages, pdir / 'transform' / 'packages.yml')}")

    if p.pipelines:
        log += _migrate_orchestration(pdir, p)

    if p.missing_capabilities:
        ctx = {"group": p.group, "project": p.project,
               "module": p.project.replace("-", "_")}
        for cap in resolve(p.missing_capabilities):
            written = apply_capability(cap, root, pdir, ctx)
            log.append(f"capability {cap.name}: {len(written)} file(s)")

    return log


def _copy_models(files: list[Path], base: Path, dest: Path) -> int:
    """Copy files, preserving their path below `base` so nothing collides."""
    n = 0
    for f in files:
        try:
            rel = f.relative_to(base)
        except ValueError:
            rel = Path(f.name)
        # Drop the incoming layer directory; the destination already is the layer.
        rel = Path(*rel.parts[1:]) if len(rel.parts) > 1 else rel
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)
        n += 1
    return n


def _merge_packages(source: Path, target: Path) -> str:
    """Union the two package lists, keeping ours on a conflict.

    Ours wins because the scaffolded `packages.yml` is pinned against what this
    platform's dbt version is tested with; taking the incoming pin could break
    every sister that shares the runtime.
    """
    try:
        incoming = (yaml.safe_load(source.read_text()) or {}).get("packages") or []
    except yaml.YAMLError as exc:
        return f"not merged, unparseable ({exc.__class__.__name__})"

    current = {}
    if target.exists():
        current = yaml.safe_load(target.read_text()) or {}
    ours = current.get("packages") or []

    def key(entry: dict) -> str:
        return str(entry.get("package") or entry.get("git") or entry.get("local") or "")

    seen = {key(e) for e in ours}
    added = [e for e in incoming if key(e) not in seen]
    if not added:
        return "no new packages"

    current["packages"] = [*ours, *added]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(current, sort_keys=False))
    return f"+{len(added)} package(s)"


def _migrate_orchestration(pdir: Path, p: Plan) -> list[str]:
    """Write the Dagster translation and quarantine every original."""
    module = p.project.replace("-", "_")

    out = pdir / "src" / module / "defs" / "migrated_pipelines.py"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(p.pipelines, module))

    quarantine = pdir / QUARANTINE
    quarantine.mkdir(parents=True, exist_ok=True)
    (quarantine / "README.md").write_text(
        "# Quarantined orchestration\n\n"
        "The original Airflow/Prefect sources, copied verbatim by `pf onboard`.\n"
        "They do not run. They are here because the generated Dagster assets in\n"
        f"`src/{module}/defs/migrated_pipelines.py` translate the task *graph* and\n"
        "not the task *bodies* — porting a body means reading the original.\n\n"
        "Delete a file here once its asset no longer raises.\n")

    for f in {x.source for x in p.pipelines}:
        shutil.copy2(f, quarantine / f.name)

    tasks = sum(len(x.tasks) for x in p.pipelines)
    return [f"dagster stubs: {tasks} asset(s) in defs/migrated_pipelines.py",
            f"quarantined {len({x.source for x in p.pipelines})} original file(s)"]
