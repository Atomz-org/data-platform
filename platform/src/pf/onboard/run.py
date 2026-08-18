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

from pf.capabilities import CAPABILITIES, resolve
from pf.capabilities import apply as apply_capability
from pf.onboard.audit import Risk, audit
from pf.onboard.dialect import AMBIGUOUS, TOOLKITS, Report, analyse
from pf.onboard.orchestrator import QUARANTINE, Pipeline, parse, render
from pf.onboard.survey import Survey, survey
from pf.scaffold.generator import new_project

#: dbt_project.yml keys the platform owns. A project may not redefine where its
#: models live or which profile it uses — those are what make it a project here
#: rather than a copy of the repository it came from.
OURS = ("name", "profile", "version", "config-version", "model-paths",
        "target-path", "clean-targets")


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
    risks: list[Risk] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checklist: list[str] = field(default_factory=list)

    @property
    def blocking(self) -> list[Risk]:
        return [r for r in self.risks if r.blocking]


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
        capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"could not clone {source}: {proc.stderr.strip()}")
    return target


def plan(root: Path, group: str, project: str, source: Path) -> Plan:
    """Work out everything that would happen, without doing any of it."""
    s = survey(source)
    p = Plan(group=group, project=project, source=source, survey=s)

    p.actions.append(Action("scaffold", f"pf new-project {group} {project}"))

    if s.dbt_project is not None:
        for layer, files in sorted(s.models.items()):
            p.actions.append(Action("models", f"transform/models/{layer}/", len(files)))
        importable = [m for m in s.macros if m.stem not in s.reserved_macros]
        if importable:
            p.actions.append(Action("macros", "transform/macros/", len(importable)))
        if s.seeds:
            p.actions.append(Action("seeds", "transform/seeds/", len(s.seeds)))
        if s.tests:
            p.actions.append(Action("tests", "transform/tests/", len(s.tests)))
        if s.snapshots:
            p.actions.append(Action("snapshots", "transform/snapshots/", len(s.snapshots)))
        if s.analyses:
            p.actions.append(Action("analyses", "transform/analyses/", len(s.analyses)))
        if s.packages:
            p.actions.append(Action("packages", "merge into transform/packages.yml"))
        p.actions.append(Action(
            "dbt_project", "merge vars and per-layer config, re-keyed to our layers"))

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

    # Every capability we have that the source does not already solve for itself,
    # minus the warehouse-specific ones it has no use for. A capability that
    # declares a warehouse is only relevant to a source that targets it —
    # otherwise every import, whatever it runs on, is handed a Snowflake
    # production target and three environment variables nobody will ever set.
    applicable = {n for n, c in CAPABILITIES.items()
                  if not c.warehouse or c.warehouse in s.warehouses}
    p.missing_capabilities = sorted(applicable - s.capabilities_present)
    for name in p.missing_capabilities:
        p.actions.append(Action("capability", name))

    # Scanned once and threaded through. The audit and the checklist both need
    # it, and on a large repository this reads every SQL file in the tree.
    report = analyse(s.sql_files(), local_macros=set(s.macro_names))
    p.risks = audit(s, root=root, dialect=report)
    _add_warnings(p)
    _add_checklist(p, report)
    return p


def _add_warnings(p: Plan) -> None:
    """Only what the audit cannot see: per-pipeline parse outcomes."""
    for pipeline in p.pipelines:
        if pipeline.error:
            p.warnings.append(f"{pipeline.source.name}: {pipeline.error}")
        elif not pipeline.tasks:
            p.warnings.append(
                f"{pipeline.source.name}: no tasks recovered — likely a dynamically "
                f"built graph; port it by hand")


def _add_checklist(p: Plan, report: Report) -> None:
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

    # Dialect ambiguity goes first because it is the only item on this list that
    # is invisible when it is wrong: the build passes and the numbers are bad.
    if report.ambiguous:
        names = ", ".join(sorted(report.ambiguous))
        p.checklist.insert(0, (
            f"Confirm the source dialect, then check every call to {names}. "
            f"These resolve on DuckDB and can return wrong values — "
            f"{AMBIGUOUS[next(iter(report.ambiguous))]}"))


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
        models_base = dbt_dir / _first_dir(s.dbt_config, "model-paths", "models")
        scaffolded = [f for f in created if "models" in f.parts]
        for layer, files in sorted(s.models.items()):
            n = _copy_models(files, models_base, pdir / "transform" / "models" / layer)
            log.append(f"models -> {layer}/: {n}")
        log += _yield_to_imported(scaffolded, s)

        # Reserved macros are left behind rather than copied. Importing one is
        # not a merge conflict anyone sees — dbt just starts putting models
        # somewhere else, and the first sign is a `pf check` failure nobody can
        # trace back to this step.
        for name in sorted(s.reserved_macros):
            log.append(f"macros: skipped {name}.sql (overrides a dbt built-in)")

        for label, files, dest in (
            ("macros", [m for m in s.macros if m.stem not in s.reserved_macros],
             pdir / "transform" / "macros"),
            ("seeds", s.seeds, pdir / "transform" / "seeds"),
            ("tests", s.tests, pdir / "transform" / "tests"),
            ("snapshots", s.snapshots, pdir / "transform" / "snapshots"),
            ("analyses", s.analyses, pdir / "transform" / "analyses"),
        ):
            if files:
                log.append(f"{label}: {_copy_tree(files, dbt_dir, dest)}")

        if s.packages:
            log.append("packages.yml: " + _merge_packages(
                s.packages, pdir / "transform" / "packages.yml", s))
        log.append(f"dbt_project.yml: {_merge_dbt_project(s, pdir / 'transform' / 'dbt_project.yml')}")

    if p.pipelines:
        log += _migrate_orchestration(pdir, p)

    if p.missing_capabilities:
        ctx = {"group": p.group, "project": p.project,
               "module": p.project.replace("-", "_")}
        for cap in resolve(p.missing_capabilities):
            written = apply_capability(cap, root, pdir, ctx)
            log.append(f"capability {cap.name}: {len(written)} file(s)")

    return log


def _yield_to_imported(scaffolded: list[Path], s: Survey) -> list[str]:
    """Remove scaffold-provided models the import brought its own versions of.

    The scaffold writes a small number of models the platform needs to exist at
    all — the MetricFlow time spine is the one today. A project that already has
    one arrives with a second, and dbt resolves models by bare name regardless of
    directory, so the pair is fatal: the project will not compile.

    The imported one wins. It is the version the project's own metrics were
    written against, and its grain and date range match the data. The platform's
    is a default for projects that have nothing, which this project is not.

    The schema entry has to go with it. A `.yml` describing a model that no
    longer exists is not a dangling reference dbt shrugs at — two entries for one
    resource name is itself a compilation error, so dropping the SQL and keeping
    the YAML swaps one fatal duplicate for another.
    """
    incoming = {f.stem for files in s.models.values() for f in files
                if f.suffix == ".sql"}
    out: list[str] = []
    dropped: set[str] = set()
    for path in sorted(p for p in scaffolded if p.suffix == ".sql"):
        if path.stem in incoming and path.exists():
            path.unlink()
            dropped.add(path.stem)
            out.append(f"models: dropped the scaffolded {path.stem}.sql — "
                       f"the import brought its own")

    for path in sorted(p for p in scaffolded if p.suffix in (".yml", ".yaml")):
        if not path.exists():
            continue
        try:
            doc = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError:
            continue
        kept = [m for m in (doc.get("models") or [])
                if (m or {}).get("name") not in dropped]
        if len(kept) == len(doc.get("models") or []):
            continue
        if kept:
            doc["models"] = kept
            path.write_text(yaml.safe_dump(doc, sort_keys=False))
            out.append(f"models: removed {len(dropped)} entr(y/ies) from {path.name}")
        else:
            path.unlink()
            out.append(f"models: dropped {path.name} — it described only "
                       f"models the import replaced")
    return out


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


def _first_dir(cfg: dict, key: str, default: str) -> str:
    raw = cfg.get(key) or default
    return raw if isinstance(raw, str) else str(raw[0])


def _copy_tree(files: list[Path], base: Path, dest: Path) -> str:
    """Copy files, preserving their path below the collected directory.

    dbt resolves macros, seeds, snapshots and tests by bare name regardless of
    directory, so it is tempting to flatten them — and flattening loses real
    information. `dbt_project.yml` configures them *by directory*: a repo whose
    seeds config reads `jaffle-data: {+enabled: ...}` is naming a subdirectory,
    and once the files are flat that key matches nothing, the config silently
    stops applying, and every seed loads that the project deliberately gated off.
    Exactly the failure the layer re-keying already had to fix, one level down.

    A name that collides is still reported rather than overwritten — losing one
    of two macros with the same name is how a project acquires behaviour nobody
    can explain — but the collision is now on the name dbt actually resolves,
    not on a path.
    """
    dest.mkdir(parents=True, exist_ok=True)
    written, clashed = 0, []
    seen: dict[str, Path] = {}
    for f in files:
        if f.stem in seen:
            clashed.append(f.name)
            continue
        seen[f.stem] = f
        try:
            rel = f.relative_to(base)
        except ValueError:
            rel = Path(f.name)
        # Drop the incoming collected directory; `dest` already is it.
        rel = Path(*rel.parts[1:]) if len(rel.parts) > 1 else rel
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)
        written += 1
    note = f", {len(clashed)} name clash(es) skipped: {', '.join(clashed[:3])}" \
        if clashed else ""
    return f"{written}{note}"


def _merge_dbt_project(s: Survey, target: Path) -> str:
    """Fold the source's dbt config into the scaffolded one.

    Three classes of key, and the split is what keeps this safe. The platform
    owns identity and layout (`name`, `profile`, `model-paths`) because those are
    what make the directory a project here. The source owns its own conventions
    (`test-paths`, `vars`, per-directory config) because those are facts about
    its models that do not stop being true on arrival — dropping the config block
    silently strips every tag and materialisation the project was written with.
    Everything else is unioned.
    """
    if not target.exists():
        return "not merged, no scaffolded file"
    try:
        ours = yaml.safe_load(target.read_text()) or {}
    except yaml.YAMLError as exc:
        return f"not merged, unparseable ({exc.__class__.__name__})"

    theirs = dict(s.dbt_config)
    kept: list[str] = []

    # Path keys are deliberately *not* carried. They are read from the source so
    # nothing is missed (a repo keeping tests in `data-tests/` really has tests),
    # and then everything is copied into this platform's standard layout. Keeping
    # the source's paths would leave the config naming directories the files were
    # moved out of, and dbt would quietly find nothing.

    if theirs.get("vars"):
        ours["vars"] = {**(ours.get("vars") or {}), **theirs["vars"]}
        kept.append("vars")

    # The per-directory config block is keyed by the *source* project name, and
    # its directory keys are the *source* layer names. Both have to be rewritten
    # or dbt silently ignores the whole thing — and a dropped block takes every
    # tag and materialisation the project was written with along with it.
    our_name = str(ours.get("name", ""))
    for section in ("models", "seeds", "snapshots"):
        incoming = (theirs.get(section) or {}).get(s.dbt_name)
        if not isinstance(incoming, dict):
            continue
        block = ours.setdefault(section, {})
        current = block.get(our_name)
        # Unrecognised directories were filed under marts/, so their config has
        # to follow them there too.
        mapping = {**s.layer_mapping, **dict.fromkeys(s.unmapped_layers, "marts")}
        merged = _remap_layers(incoming, mapping)
        # Ours last, so the platform's materialisation and schema settings win
        # any key the source also sets.
        block[our_name] = _deep_merge(
            merged, current if isinstance(current, dict) else {})
        kept.append(section)

    # The dialect toolkits are reached through `macro-paths`, which the scaffold
    # already wrote. Re-assert it here so a project onboarded over an older
    # scaffold still gets the portable macros rather than failing on the first
    # `{{ sf_iff(...) }}` someone writes.
    paths = ours.get("macro-paths") or []
    paths = [paths] if isinstance(paths, str) else list(paths)
    for toolkit in TOOLKITS:
        entry = f"../../../../../platform/toolkits/{toolkit}/macros"
        if entry not in paths:
            paths.append(entry)
            kept.append(f"macro-paths+{toolkit}")
    ours["macro-paths"] = paths

    target.write_text(yaml.safe_dump(ours, sort_keys=False))
    return f"merged {', '.join(kept)}" if kept else "nothing to merge"


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursive dict merge, `override` winning at every depth."""
    out = dict(base)
    for key, value in override.items():
        current = out.get(key)
        out[key] = _deep_merge(current, value) if isinstance(current, dict) \
            and isinstance(value, dict) else value
    return out


def _remap_layers(block: dict, mapping: dict[str, str]) -> dict:
    """Rewrite a config block's directory keys to the layers the files moved to.

    The models were re-filed on the way in — `bronze/` became `staging/`, and
    `intermediate/` and `marts/` both became `marts/`. A config block still keyed
    by the old names configures directories that no longer exist, which dbt
    accepts in silence. The tags simply stop applying, and nothing anywhere says
    so.

    Two source layers can collapse onto one of ours, so blocks are merged rather
    than overwritten.
    """
    out: dict = {}
    for key, value in block.items():
        # `+materialized` and friends apply to the whole block, not a directory.
        target_key = key if key.startswith("+") else mapping.get(key.lower(), key)
        current = out.get(target_key)
        out[target_key] = _deep_merge(current, value) \
            if isinstance(current, dict) and isinstance(value, dict) else value
    return out


def _merge_packages(source: Path, target: Path, survey: Survey | None = None) -> str:
    """Union the two package lists, keeping ours on a conflict.

    Ours wins because the scaffolded `packages.yml` is pinned against what this
    platform's dbt version is tested with; taking the incoming pin could break
    every sister that shares the runtime.

    One package is dropped rather than merged: an unpinned git dependency with no
    detected call sites. Either condition alone is only worth reporting — the
    namespace is guessed, so a zero count can be wrong — but together they mean
    importing a dependency that makes every build resolve differently and buys
    nothing. That runs against this repository's rule that upstream versions are
    a human decision, and the log line says what was left behind.
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

    unpinned = {u.split(" @ ")[0] for u in (survey.unpinned_packages if survey else [])}
    usage = survey.package_usage if survey else {}

    seen = {key(e) for e in ours}
    added, dropped = [], []
    for entry in incoming:
        k = key(entry)
        if k in seen:
            continue
        if k in unpinned and usage.get(k, 1) == 0:
            dropped.append(k)
        else:
            added.append(entry)

    note = (f"; dropped {len(dropped)} unpinned and unused: {', '.join(dropped)}"
            if dropped else "")
    if not added:
        return f"no new packages{note}"

    current["packages"] = [*ours, *added]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(current, sort_keys=False))
    return f"+{len(added)} package(s){note}"


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
