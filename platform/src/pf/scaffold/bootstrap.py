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

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

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
    run: Callable[[Path, str, str], StepResult]


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
    n = estimate_tokens(p.read_text())
    status: Status = "ok" if n <= PROJECT_CARD_BUDGET else "failed"
    return StepResult("context card", status, f"~{n} tokens / {PROJECT_CARD_BUDGET}")


def _render_group_card(root: Path, group: str, project: str) -> StepResult:
    from pf.kg.card import render_group_card

    render_group_card(root / "groups" / group, group)
    return StepResult("group card", "ok", "sister roster refreshed")


def _render_context(root: Path, group: str, project: str) -> StepResult:
    """Regenerate the toolkit index and this project's capability card.

    Runs on every bootstrap, which is what keeps the card honest: `pf capability-add`
    bootstraps after applying, so a capability can never be present in a project
    while absent from the context every agent in it reads.
    """
    from pf.context import build, problems

    written = build(root, group, project)
    broken = problems(root)
    detail = ", ".join(p.name for p in written)
    if broken:
        # Not a failure: the index still renders. But a toolkit whose frontmatter
        # does not parse has silently contributed no rules at all.
        return StepResult("toolkit index + capability card", "ok",
                          f"{detail} — unparseable frontmatter: {'; '.join(broken)}")
    return StepResult("toolkit index + capability card", "ok", detail)


def _export_mdl(root: Path, group: str, project: str) -> StepResult:
    """The BI/agent projection. Emitted even when empty so the path is stable and
    a consumer can be pointed at it before the first model exists."""
    from pf.projections.mdl import export as export_mdl

    path = export_mdl(_pdir(root, group, project), group, project)
    import json

    m = json.loads(path.read_text())
    return StepResult("MDL manifest", "ok",
                      f"{len(m['models'])} model(s), {len(m['relationships'])} relationship(s)")


def _export_owl(root: Path, group: str, project: str) -> StepResult:
    """Platform-level and shared, so it is written once rather than per project."""
    from pf.projections.owl import export as export_owl, stats

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
    n = estimate_tokens(card.read_text())
    status: Status = "ok" if n <= VENDOR_CARD_BUDGET else "failed"
    return StepResult("vendor docs", status, f"card ~{n} / {VENDOR_CARD_BUDGET} tokens")


def _export_otop(root: Path, group: str, project: str) -> StepResult:
    """The governance projection, with this project's evidence resolved live.

    Per project rather than platform-wide because the policies are shared but the
    evidence is not: the same rule passes in one project and fails in another,
    and a manifest that averaged them would be true of nowhere.
    """
    from pf.projections.otop import build_manifest, export as export_otop, stats

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
    d = _pdir(root, group, project)
    if not (d / "reporting").exists():
        return StepResult("reporting", "skipped", "no reporting/ (add --with evidence)")
    from pf.projections.evidence import build as build_evidence

    r = build_evidence(d, group, project)
    return StepResult("reporting", "ok",
                      f"{r['metrics']} metric(s), {r['pages']} page(s)")


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
    (root / "platform" / "workspace.yaml").write_text("\n".join(lines) + "\n")
    return StepResult("dagster code location", "ok", f"{n} location(s)")


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
    Step("toolkit index + capability card",
         "what exists and what is forbidden, in context before the mistake rather "
         "than in a file the agent would have had to know to open", _render_context),
    Step("MDL manifest", "the BI / WrenAI projection; stable path before first model",
         _export_mdl),
    Step("OWL export", "RDF-XML for external ontology tooling", _export_owl),
    Step("otop manifest", "policy and evidence as an OpenTopology 0.2 graph; "
                          "validated against the vendored schema", _export_otop),
    Step("vendor docs", "provenance stays generated, so it cannot drift from the "
                        "registry the tooling reads", _vendor_docs),
    Step("reporting", "dashboards are a projection of the metrics, regenerated "
                      "rather than hand-maintained", _build_reporting),
    Step("dagster code location", "an unregistered project never runs",
         _register_code_location),
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
            results.append(step.run(root, group, project))
        except Exception as exc:  # noqa: BLE001 — a step failing is data, not a crash
            results.append(StepResult(step.name, "failed",
                                      f"{type(exc).__name__}: {exc}"[:200]))
    return results
