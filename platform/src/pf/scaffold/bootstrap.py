"""Everything a project needs beyond its files, in one ordered, idempotent place.

Why this module exists: the post-write steps used to be inlined in
`pf new-project`. That made them unreachable for projects created earlier, so
every platform capability added afterwards had to be retrofitted by hand — the
PreToolUse hook, the dbt macro-paths and the placeholder context card were all
patched across existing projects with one-off scripts. Each of those was a silent
hole until someone noticed.

Now there is exactly one list. `pf new-project` runs it; `pf bootstrap` re-runs it
over any project, new or old. Adding a capability means adding a step here, and
both paths pick it up.

Every step must be **idempotent** — `pf bootstrap --all` is expected to be run
repeatedly — and **tolerant of an empty project**: a freshly scaffolded project
has no sources, no models and no warehouse, and bootstrapping it must still work.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Status = Literal["ok", "skipped", "failed"]


@dataclass
class StepResult:
    name: str
    status: Status
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status != "failed"


@dataclass(frozen=True)
class Step:
    name: str
    why: str
    #: May return several results. A step that fans out over a variable number of
    #: things — one entry per enabled tool — would otherwise have to flatten
    #: itself into a single line, and "3 tools ok" hides which one is broken.
    run: Callable[[Path, str, str], StepResult | list[StepResult]]


# ------------------------------------------------------------------ steps --
def _ensure_dirs(root: Path, group: str, project: str) -> StepResult:
    d = _pdir(root, group, project)
    made = []
    for rel in ("data", "kg", "contracts", "mdl", "governance", ".duckdb-skills",
                "decisions", ".memory/notes", "evals/cases"):
        p = d / rel
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            made.append(rel)
    return StepResult("directories", "ok", f"created {len(made)}" if made else "present")


def _build_graph(root: Path, group: str, project: str) -> StepResult:
    from pf.kg.build import build_graph

    counts = build_graph(_pdir(root, group, project), group=group, project=project)
    return StepResult("knowledge graph", "ok",
                      f"{sum(counts.values())} nodes across {len(counts)} kinds")


def _render_card(root: Path, group: str, project: str) -> StepResult:
    from pf.kg.card import PROJECT_CARD_BUDGET, estimate_tokens, render_project_card

    p = render_project_card(_pdir(root, group, project), group, project)
    n = estimate_tokens(p.read_text(encoding="utf-8"))
    status: Status = "ok" if n <= PROJECT_CARD_BUDGET else "failed"
    return StepResult("context card", status, f"~{n} tokens / {PROJECT_CARD_BUDGET}")


def _render_group_card(root: Path, group: str, project: str) -> StepResult:
    from pf.kg.card import render_group_card

    render_group_card(root / "groups" / group, group)
    return StepResult("group card", "ok", "sister roster refreshed")


def _export_mdl(root: Path, group: str, project: str) -> StepResult:
    """The BI/agent projection. Emitted even when empty so the path is stable and
    a consumer can be pointed at it before the first model exists."""
    from pf.projections.mdl import export as export_mdl

    path = export_mdl(_pdir(root, group, project), group, project)
    import json

    m = json.loads(path.read_text(encoding="utf-8"))
    return StepResult("MDL manifest", "ok",
                      f"{len(m['models'])} model(s), {len(m['relationships'])} relationship(s)")


def _export_owl(root: Path, group: str, project: str) -> StepResult:
    """Platform-level and shared, so it is written once rather than per project."""
    from pf.projections.owl import export as export_owl
    from pf.projections.owl import stats

    export_owl(root / "platform" / "src" / "pf" / "ontology" / "ontology.owl")
    s = stats()
    return StepResult("OWL export", "ok",
                      f"{s['classes']} classes, {s['object_properties']} object properties")


def _vendor_docs(root: Path, group: str, project: str) -> StepResult:
    """Regenerate the provenance docs from the registry.

    Platform-level and idempotent, so it is written once rather than per project.
    Generated for the same reason everything else here is: a hand-written page
    beside a machine-read registry is two accounts of one fact, and one of them
    goes quietly wrong.
    """
    from pf.kg.card import estimate_tokens
    from pf.vendor.card import VENDOR_CARD_BUDGET, render_card, render_doc

    render_doc(root)
    card = render_card(root)
    n = estimate_tokens(card.read_text(encoding="utf-8"))
    status: Status = "ok" if n <= VENDOR_CARD_BUDGET else "failed"
    return StepResult("vendor docs", status, f"card ~{n} / {VENDOR_CARD_BUDGET} tokens")


def _export_otop(root: Path, group: str, project: str) -> StepResult:
    """The governance projection, with this project's evidence resolved live.

    Per project rather than platform-wide because the policies are shared but the
    evidence is not: the same rule passes in one project and fails in another,
    and a manifest that averaged them would be true of nowhere.
    """
    from pf.projections.otop import build_manifest, stats
    from pf.projections.otop import export as export_otop

    d = _pdir(root, group, project)
    export_otop(root, group, project, d)
    s = stats(build_manifest(root, group, project, d))
    unknown = s.get("evidence_unknown", 0)
    return StepResult("otop manifest", "ok",
                      f"{s.get('constraint', 0)} constraint(s), "
                      f"{s.get('evidence', 0)} evidence"
                      + (f", {unknown} unproven" if unknown else ""))


def _build_reporting(root: Path, group: str, project: str) -> StepResult:
    """Regenerate the Evidence layer, but only where it was opted into.

    Skipped rather than created when `reporting/` is absent: the reporting layer
    is a capability, and bootstrap must not silently enable one nobody asked for.
    """
    from pf.tools.evidence import bootstrap_project

    d = _pdir(root, group, project)
    r = bootstrap_project(root, group, project, d, {})
    return StepResult("reporting", r.status, r.detail)


def _group_notify(root: Path, group: str, project: str) -> StepResult:
    """The group's delivery channel file, for groups scaffolded before it existed.

    Group-level, so it is written once per family and not once per sister; the
    step is still per project because bootstrap is, and the second sister finds
    it present.
    """
    import re

    from pf.scaffold.generator import GROUP_NOTIFY, render

    f = root / "groups" / group / "notify.yaml"
    if f.exists():
        return StepResult("notify channel", "ok", "present")
    ctx = {"group": group, "group_upper": re.sub(r"[^A-Z0-9]+", "_", group.upper())}
    f.write_text(render(GROUP_NOTIFY, ctx), encoding="utf-8")
    return StepResult("notify channel", "ok", f"wrote {f.relative_to(root)}")


def _bootstrap_tools(root: Path, group: str, project: str) -> list[StepResult]:
    """Every tool this project enables, set up idempotently.

    One step for all tools rather than a step per tool: which tools exist is not
    knowable here — a third party can add one by installing a package — so the
    list has to be resolved at run time. This is the seam that makes a tool reach
    projects created before it existed, exactly as this module does for platform
    steps.
    """
    from pf.tools import bootstrap_tools, enabled_names

    names = enabled_names(root, group, project)
    if not names:
        return [StepResult("tools", "skipped", "none enabled (`pf tool enable`)")]
    return bootstrap_tools(root, group, project)


def _bootstrap_capabilities(root: Path, group: str, project: str) -> list[StepResult]:
    """Every default-enabled capability, applied to this project if it is missing.

    The sibling of `_bootstrap_tools`, and it exists for the same failure: a
    capability used to reach only the projects whose author passed `--with`, so
    the impact-gate workflow existed for one project out of eight and nobody
    could see that from inside the other seven.

    Backfill applies a capability only when **every** file it writes is absent,
    never when some already exist. `pf.capabilities.apply` rewrites each target
    wholesale, and not every target is fully generated: `transform/profiles.yml`
    is seeded once and then hand-maintained — projects carry `extensions:` and
    per-target comments that `PROJECT_TARGETS` does not know about, and
    `_dbt_wiring` deliberately only *appends* absent targets rather than
    regenerating it. A partial backfill would silently delete that.

    So a partially-present capability is reported, not applied: switching it on
    rewrites a file someone edited, and that is a decision to take deliberately
    with `pf capability-add`. A fresh project has none of the files, so
    `pf new-project` still gets the whole default set.
    """
    from pf.capabilities import CAPABILITIES, defaults, render
    from pf.capabilities import apply as apply_capability

    d = _pdir(root, group, project)
    ctx = {"group": group, "project": project, "module": project.replace("-", "_")}
    out: list[StepResult] = []

    for name in defaults():
        cap = CAPABILITIES[name]
        # `.github/**` belongs to the repository, not the project — the same
        # split `pf.capabilities.apply` makes when writing.
        targets = [
            (root if rel.startswith(".github/") else d) / rel
            for rel in (render(r, ctx) for r in cap.files)
        ]
        present = [t for t in targets if t.exists()]
        if len(present) == len(targets):
            out.append(StepResult(f"capability:{name}", "ok", "present"))
            continue
        if present:
            out.append(StepResult(
                f"capability:{name}", "skipped",
                f"{len(present)}/{len(targets)} file(s) already exist "
                f"(would rewrite {present[0].name}) — "
                f"`pf capability-add {name} {group} {project}` to apply deliberately"))
            continue
        try:
            written = apply_capability(cap, root, d, ctx)
            # `apply` writes files and merges settings; the gate half is a
            # separate call in `pf new-project`. Backfilling the files without it
            # would leave a project whose generated artefacts nothing denies —
            # the capability present, its guard rail absent.
            from pf.capabilities import gate_additions
            from pf.cli import _merge_gate_rules

            _merge_gate_rules(gate_additions([cap]))
        except Exception as exc:  # noqa: BLE001 — one capability must not stop the rest
            out.append(StepResult(f"capability:{name}", "failed", str(exc)))
            continue
        out.append(StepResult(f"capability:{name}", "ok",
                              f"added {len(written)} file(s)"))

    if not out:
        return [StepResult("capabilities", "skipped", "none default-enabled")]
    return out


def _ci_workflow(root: Path, group: str, project: str) -> StepResult:
    """One workflow per project, composed from every job its capabilities declare.

    Replaces the file-per-capability arrangement, where each capability shipped a
    whole `.github/workflows/<thing>-<project>.yml`. Sixteen files for eight
    projects, each with its own trigger, its own path filter and its own
    checkout, and no single place that answered "what does CI do for this
    project". The per-capability files this supersedes are removed here rather
    than left behind, because leaving them means every PR runs both.

    Which jobs apply is asked, not assumed: a tool switched off in this project's
    `tools.yaml` does not contribute its job, so opting out of recce removes the
    review job rather than leaving a job that fails.
    """
    from pf.capabilities import CAPABILITIES, defaults
    from pf.scaffold.ci import legacy_paths, render_project_workflow, workflow_path
    from pf.tools import enabled_names

    try:
        names = set(defaults()) | set(enabled_names(root, group, project))
    except Exception:  # noqa: BLE001 — a broken tool registry must not stop bootstrap
        names = set(defaults())

    jobs: dict[str, str] = {}
    for name in sorted(names):
        cap = CAPABILITIES.get(name)
        if cap is not None:
            jobs.update(cap.ci_jobs)

    target = root / workflow_path(project)
    if not jobs:
        return StepResult("ci workflow", "skipped", "no capability contributes a job")

    target.parent.mkdir(parents=True, exist_ok=True)
    content = render_project_workflow(group, project, jobs)
    changed = not target.exists() or target.read_text(encoding="utf-8") != content
    if changed:
        target.write_text(content, encoding="utf-8")

    removed = []
    for rel in legacy_paths(project):
        old = root / rel
        if old.exists():
            old.unlink()
            removed.append(Path(rel).name)

    detail = f"{len(jobs)} job(s): {', '.join(sorted(jobs))}"
    if removed:
        detail += f" · superseded {', '.join(removed)}"
    elif not changed:
        detail += " · current"
    return StepResult("ci workflow", "ok", detail)


def _register_code_location(root: Path, group: str, project: str) -> StepResult:
    """An unregistered project silently never runs in Dagster."""
    from pf.cli import all_projects

    lines = ["# GENERATED by `pf bootstrap`. Re-run after adding a project.",
             "#",
             "# One code location per project: a failure or reload in one sister never",
             "# affects another, and each gets its own process.",
             "load_from:"]
    n = 0
    for g, p, d in all_projects():
        module = p.replace("-", "_")
        if not (d / "src" / module / "definitions.py").exists():
            continue
        lines += ["  - python_module:",
                  f"      module_name: {module}.definitions",
                  f"      working_directory: {(d / 'src').resolve()}",
                  f"      location_name: {g}__{p}"]
        n += 1
    (root / "platform" / "workspace.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return StepResult("dagster code location", "ok", f"{n} location(s)")


def _dbt_wiring(root: Path, group: str, project: str) -> StepResult:
    """Keep an existing project's dbt config in step with the platform's.

    Two things drift, and both drift silently. A project scaffolded before a
    dialect toolkit existed has no `macro-paths` entry for it, so every `sf_*`
    call site in it fails to compile with "macro not found" — an error that
    points at the model rather than at the missing path. And a project with no
    `base` target cannot be diffed by Recce at all, because Recce compares two
    built states and there is nowhere to build the other one.

    Rewritten in place rather than regenerated, so a project's own edits to its
    dbt_project.yml survive. Text-level for `macro-paths` because a YAML
    round-trip would reflow the whole file and lose the comments explaining why
    the platform macros are on the path in the first place.
    """
    import yaml

    from pf.onboard.dialect import TOOLKITS
    from pf.runtime.targets import default_warehouse
    from pf.scaffold.generator import (
        PROJECT_TARGETS,
        render_target,
        replace_target,
        target_type,
    )

    d = _pdir(root, group, project)
    changed: list[str] = []

    dbt_yml = d / "transform" / "dbt_project.yml"
    if dbt_yml.exists():
        text = dbt_yml.read_text(encoding="utf-8")
        try:
            paths = [str(p) for p in
                     (yaml.safe_load(text) or {}).get("macro-paths") or []]
        except yaml.YAMLError:
            paths = []
        wanted = [f"../../../../../platform/toolkits/{t}/macros" for t in TOOLKITS]
        missing = [w for w in wanted if not any(w in p for p in paths)]
        if missing and "macro-paths:" in text:
            lines = text.splitlines()
            out, inserted = [], False
            for i, line in enumerate(lines):
                out.append(line)
                nxt = lines[i + 1] if i + 1 < len(lines) else ""
                if (not inserted and line.lstrip().startswith("- ")
                        and any(p in line for p in paths)
                        and not nxt.lstrip().startswith("- ")):
                    out += [f'  - "{m}"' for m in missing]
                    inserted = True
            if inserted:
                dbt_yml.write_text("\n".join(out) + "\n", encoding="utf-8")
                changed.append(f"macro-paths += {len(missing)}")

    profiles = d / "transform" / "profiles.yml"
    if profiles.exists():
        text = profiles.read_text(encoding="utf-8")
        try:
            doc = yaml.safe_load(text) or {}
        except yaml.YAMLError:
            doc = {}
        outputs = next((v.get("outputs") or {} for v in doc.values()
                        if isinstance(v, dict) and "outputs" in v), {})
        # Only ever adds. A project that has retargeted `prod` at a real
        # warehouse must not have it reset to the DuckDB default by a step whose
        # job is to fill gaps.
        absent = [n for n in PROJECT_TARGETS if outputs and n not in outputs]
        if absent:
            text = (text.rstrip("\n") + "\n"
                    + "".join(render_target(n, PROJECT_TARGETS[n]) for n in absent))
            profiles.write_text(text, encoding="utf-8")
            changed.append(f"profiles += {', '.join(absent)}")

        # Point `prod` at the production warehouse, if it is still the DuckDB
        # placeholder.
        #
        # The placeholder exists so a scaffolded project builds before anyone has
        # decided where production lives. Left there it is a quiet lie: `prod`
        # names a target that is a local file, so `DBT_TARGET=prod dbt build`
        # succeeds, writes nothing anyone can see, and reports success. Seven of
        # eight projects were in that state.
        #
        # Guarded on the *current* type, not on whether we have written here
        # before. Anything already pointing at a real engine — Snowflake set by
        # hand, BigQuery from `pf capability-add` — is left exactly alone, so
        # this can never take a project off its own warehouse. And only the
        # `prod` block is touched: `replace_target` is text-level precisely so
        # hand-added keys on the DuckDB targets beside it survive.
        wh = default_warehouse()
        if wh is not None and outputs:
            current = target_type(text, "prod")
            if current == "duckdb":
                new_text, swapped = replace_target(text, "prod", wh.output)
                if swapped:
                    profiles.write_text(new_text, encoding="utf-8")
                    changed.append(f"prod -> {wh.name}")
            elif current and current != wh.name:
                changed.append(f"prod already on {current}, left alone")

    if not changed:
        return StepResult("dbt wiring", "ok", "macro-paths and targets current")
    return StepResult("dbt wiring", "ok", "; ".join(changed))


def _validate(root: Path, group: str, project: str) -> StepResult:
    from pf.ontology.validate import validate_project

    issues = validate_project(_pdir(root, group, project))
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        return StepResult("conformance", "failed",
                          "; ".join(str(i) for i in errors[:3]))
    return StepResult("conformance", "ok",
                      f"{len(issues)} warning(s)" if issues else "clean")


STEPS: list[Step] = [
    Step("directories", "every generated artefact has a stable home", _ensure_dirs),
    Step("knowledge graph", "kg_search, impact and the PreToolUse gate need a graph "
                            "from day one, not after the first seed", _build_graph),
    Step("context card", "the always-on index every session loads", _render_card),
    Step("group card", "sister roster, so a new project is visible to its siblings",
         _render_group_card),
    Step("MDL manifest", "the BI / WrenAI projection; stable path before first model",
         _export_mdl),
    Step("OWL export", "RDF-XML for external ontology tooling", _export_owl),
    Step("otop manifest", "policy and evidence as an OpenTopology 0.2 graph; "
                          "validated against the vendored schema", _export_otop),
    Step("vendor docs", "provenance stays generated, so it cannot drift from the "
                        "registry the tooling reads", _vendor_docs),
    Step("reporting", "dashboards are a projection of the metrics, regenerated "
                      "rather than hand-maintained", _build_reporting),
    Step("tools", "a tool enabled for the group must reach every sister, "
                  "including projects created before it existed", _bootstrap_tools),
    Step("capabilities", "a default-enabled capability must reach every project, "
                         "including ones scaffolded before it was a default",
         _bootstrap_capabilities),
    Step("notify channel", "where loops and answers are delivered; names an env "
                           "var, never a URL", _group_notify),
    Step("ci workflow", "one workflow per project, composed from the jobs its "
                        "capabilities declare, so CI is readable in one place",
         _ci_workflow),
    Step("dagster code location", "an unregistered project never runs",
         _register_code_location),
    Step("dbt wiring", "a project scaffolded before a toolkit existed cannot "
                       "compile its macros, and one with no base target cannot "
                       "be diffed", _dbt_wiring),
    Step("conformance", "fail here rather than in BI", _validate),
]


def _pdir(root: Path, group: str, project: str) -> Path:
    return root / "groups" / group / "projects" / project


def bootstrap(root: Path, group: str, project: str) -> list[StepResult]:
    """Run every step. Failures are reported, not raised: one broken step must not
    leave a project half-registered."""
    results: list[StepResult] = []
    for step in STEPS:
        try:
            out = step.run(root, group, project)
        except Exception as exc:  # noqa: BLE001 — a step failing is data, not a crash
            results.append(StepResult(step.name, "failed",
                                      f"{type(exc).__name__}: {exc}"[:200]))
            continue
        results.extend(out if isinstance(out, list) else [out])
    return results
