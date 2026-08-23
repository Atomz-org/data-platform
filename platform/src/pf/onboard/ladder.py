"""The onboarding ladder — a parent loop of stages, each a child loop.

Onboarding a repository is not one act. Adopting the files is the cheap part;
what takes the work is making the project mean something to this platform — its
ontology, its layers, its metrics, its review discipline. Those have a strict
order, because each one consumes what the previous produced:

    import  ->  ontology  ->  dialect  ->  layers  ->  metrics  ->  review

Annotations cannot be written against models whose SQL will not compile. Layers
cannot be judged before the SQL parses. Metrics cannot be defined before the
marts they measure are in `marts/`. Recce cannot diff a project that has never
built. Run them out of order and each stage is redone when the one before it
lands, which is the failure this ladder exists to stop.

Every stage is itself a loop of three phases:

``evaluate``   deterministic, read-only, zero tokens. Returns findings.
``implement``  the agent's work. Not in this module — a stage names the skill
               reference that describes it, and nothing here writes SQL.
``validate``   deterministic gate. Returns checks with evidence.

**Why evaluate and validate are code and implement is not.** A loop whose gate is
prose gets talked out of its verdict; this repository has the scar to prove it
(`LOOP.md`, "Agent skips the impact gate"). So the two phases that decide whether
a stage is finished are executable and cost nothing to run, and the phase that
needs judgement is the only one left to an agent.

**Verdicts are derived, never recorded.** `status` re-reads the project every
time rather than trusting a state file, because a recorded pass survives the
change that invalidated it. Attempt *counts* are recorded — in the loop ledger,
via `pf.loops.runner` — because "how many times have we tried this" cannot be
re-derived, and losing it on restart is how a loop retries forever.

A check is `pass`, `fail`, or `unexercised`. The third is not a polite failure:
it is the honest answer when the tool that would decide is not installed, and it
is reported loudly rather than counted as either. Only `fail` closes the gate —
a missing MetricFlow CLI must not wall a project off from the rest of the ladder.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Literal

import yaml

from pf.onboard.audit import Risk
from pf.onboard.dialect import Report, analyse
from pf.onboard.survey import RESERVED_MACROS

Status = Literal["pass", "fail", "unexercised"]

#: The layers this platform reasons about. `semantic` is not a model directory in
#: the same sense as the others — it holds MetricFlow YAML — but it lives under
#: `models/` and dbt parses it there, so the ladder treats it as a layer.
LAYERS = ("staging", "marts", "semantic", "utils")

#: Layers that must carry a materialisation and schema config. `semantic` holds
#: no compiled SQL, so a config block for it would configure nothing.
CONFIGURED_LAYERS = ("staging", "marts")

#: Warehouse type expected on each named dbt target. Development is DuckDB
#: because a developer must be able to build the whole project on a laptop with
#: no credentials; production is whatever the business actually runs, declared
#: per project. `None` means any type is acceptable.
TARGET_TYPES: dict[str, str | None] = {"dev": "duckdb", "base": "duckdb", "prod": None}

_REF = re.compile(r"\{\{\s*(?:ref|source)\s*\(([^)]*)\)", re.IGNORECASE)


# ------------------------------------------------------------------ checks --
@dataclass(frozen=True)
class Check:
    """One gate condition, with the evidence for its verdict.

    `evidence` is not a restatement of `name`. A check that says only "failed"
    forces whoever reads it to reproduce the check by hand, which is how a gate
    stops being read at all.
    """

    name: str
    status: Status
    evidence: str

    @property
    def ok(self) -> bool:
        return self.status != "fail"


def passed(name: str, evidence: str) -> Check:
    return Check(name, "pass", evidence)


def failed(name: str, evidence: str) -> Check:
    return Check(name, "fail", evidence)


def unexercised(name: str, evidence: str) -> Check:
    return Check(name, "unexercised", evidence)


@dataclass
class Verdict:
    stage: str
    checks: list[Check] = field(default_factory=list)

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if c.status == "fail"]

    @property
    def gaps(self) -> list[Check]:
        return [c for c in self.checks if c.status == "unexercised"]

    @property
    def open(self) -> bool:
        """Whether the next stage may be entered."""
        return not self.failures

    @property
    def complete(self) -> bool:
        """Whether every condition was actually exercised and passed."""
        return not self.failures and not self.gaps

    @property
    def summary(self) -> str:
        if self.failures:
            return f"{len(self.failures)} of {len(self.checks)} checks failed"
        if self.gaps:
            return f"passed with {len(self.gaps)} check(s) not exercised"
        return f"all {len(self.checks)} checks passed"


# ----------------------------------------------------------------- context --
@dataclass
class Ctx:
    """Everything a stage reads, computed once.

    The dialect scan alone reads every SQL file in the project. Six stages each
    doing that independently turned a one-second ladder into a six-second one
    for no new information, so the expensive reads are cached here and threaded
    through instead.
    """

    root: Path
    group: str
    project: str

    @property
    def pdir(self) -> Path:
        return self.root / "groups" / self.group / "projects" / self.project

    @property
    def transform(self) -> Path:
        return self.pdir / "transform"

    @property
    def duckdb_path(self) -> Path:
        return self.pdir / "data" / f"{self.project.replace('-', '_')}.duckdb"

    @cached_property
    def dbt_config(self) -> dict:
        p = self.transform / "dbt_project.yml"
        if not p.exists():
            return {}
        try:
            return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            return {}

    @cached_property
    def profiles(self) -> dict:
        p = self.transform / "profiles.yml"
        if not p.exists():
            return {}
        try:
            return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            return {}

    @cached_property
    def outputs(self) -> dict[str, dict]:
        """target name -> its output block, for this project's own profile."""
        for block in self.profiles.values():
            if isinstance(block, dict) and "outputs" in block:
                return block.get("outputs") or {}
        return {}

    @cached_property
    def models(self) -> dict[str, list[Path]]:
        """Top-level model directory -> the .sql files under it."""
        out: dict[str, list[Path]] = {}
        base = self.transform / "models"
        if not base.exists():
            return out
        for f in sorted(base.rglob("*.sql")):
            rel = f.relative_to(base)
            layer = rel.parts[0] if len(rel.parts) > 1 else ""
            out.setdefault(layer, []).append(f)
        return out

    @cached_property
    def sql_files(self) -> list[Path]:
        roots = ("models", "macros", "tests", "snapshots", "analyses")
        return [f for d in roots for f in sorted((self.transform / d).rglob("*.sql"))]

    @cached_property
    def dialect(self) -> Report:
        local = {f.stem for f in (self.transform / "macros").rglob("*.sql")}
        return analyse(self.sql_files, local_macros=local)

    @cached_property
    def semantic_yaml(self) -> list[dict]:
        out = []
        for f in sorted((self.transform / "models" / "semantic").rglob("*.yml")):
            try:
                doc = yaml.safe_load(f.read_text(encoding="utf-8"))
            except yaml.YAMLError:
                continue
            if isinstance(doc, dict):
                out.append(doc)
        return out

    @cached_property
    def annotations(self) -> list:
        from pf.ontology.annotate import load_annotations

        return load_annotations(self.pdir / "contracts" / "annotations.yaml")

    @cached_property
    def unmodelled(self) -> dict[str, str]:
        from pf.ontology.annotate import load_unmodelled

        return load_unmodelled(self.pdir / "contracts" / "annotations.yaml")

    def dbt(self, *args: str, target: str = "dev") -> subprocess.CompletedProcess:
        from pf.runtime.dbt_runtime import dbt

        return dbt(self.pdir, *args, target=target, duckdb_path=self.duckdb_path)


# ------------------------------------------------------------------ stages --
@dataclass(frozen=True)
class Stage:
    name: str
    title: str
    #: What this stage is responsible for, in one line. Printed by `pf align`.
    subject: str
    #: The skill reference an agent reads to do the implement phase.
    reference: str
    evaluate: Callable[[Ctx], list[Risk]]
    validate: Callable[[Ctx], list[Check]]
    #: Project-relative globs this stage is allowed to write. The checker rejects
    #: a change outside them — loop-engineering's first verifier condition, made
    #: mechanical. A stage that may touch anything cannot be scope-checked, and a
    #: verifier that cannot check scope approves drive-by refactors.
    owns: tuple[str, ...] = ()
    #: Per-run ceiling when the stage is driven through `pf.loops.runner`.
    token_budget: int = 0


def _fmt(counter: Counter, limit: int = 6) -> str:
    top = counter.most_common(limit)
    shown = ", ".join(f"{name} x{n}" for name, n in top)
    rest = len(counter) - len(top)
    return f"{shown}{f', +{rest} more' if rest > 0 else ''}"


def _upstreams(path: Path) -> set[str]:
    """Distinct `ref`/`source` targets a model reads, by textual scan.

    Textual rather than from the manifest on purpose: this runs before the
    project is guaranteed to parse, and a stage that needs a manifest to tell you
    why the manifest will not build is no use.
    """
    try:
        text = path.read_text(errors="ignore", encoding="utf-8")
    except OSError:
        return set()
    return {m.group(1).strip() for m in _REF.finditer(text)}


# ================================================================== import ==
def eval_import(c: Ctx) -> list[Risk]:
    out: list[Risk] = []
    if not c.pdir.exists():
        return [Risk("not-imported", "blocks",
                     f"no project at groups/{c.group}/projects/{c.project}",
                     f"Run `pf onboard {c.group} {c.project} <source> --apply`.")]
    if not (c.transform / "dbt_project.yml").exists():
        out.append(Risk("no-dbt-project", "blocks",
                        "the project has no transform/dbt_project.yml",
                        "The import did not complete. Re-run `pf onboard`."))

    stems = Counter(f.stem for files in c.models.values() for f in files)
    dupes = Counter({n: k for n, k in stems.items() if k > 1})
    if dupes:
        out.append(Risk("name-collision", "blocks",
                        f"{len(dupes)} model name(s) defined more than once: {_fmt(dupes)}",
                        "dbt resolves models by bare name regardless of directory, "
                        "so these must be renamed before anything compiles."))

    reserved = sorted({f.stem for f in (c.transform / "macros").rglob("*.sql")}
                      & set(RESERVED_MACROS))
    if reserved:
        out.append(Risk("reserved-macro", "blocks",
                        f"the project overrides dbt built-in(s): {', '.join(reserved)}",
                        "Each one changes where models land or how lineage is "
                        "resolved. Delete, or confirm it agrees with this "
                        "platform's layout and record why in decisions/."))

    if not any(c.models.values()):
        out.append(Risk("no-models", "blocks", "no model files were imported",
                        "Check the source path and its `model-paths`."))
    return out


def check_import(c: Ctx) -> list[Check]:
    checks: list[Check] = []
    checks.append(passed("project exists", str(c.pdir.relative_to(c.root)))
                  if c.pdir.exists() else
                  failed("project exists", f"{c.pdir} not found"))
    if not c.pdir.exists():
        return checks

    total = sum(len(v) for v in c.models.values())
    checks.append(passed("models imported",
                         f"{total} model(s) across {len(c.models)} director(y/ies)")
                  if total else failed("models imported", "models/ holds no .sql"))

    stems = Counter(f.stem for files in c.models.values() for f in files)
    dupes = [n for n, k in stems.items() if k > 1]
    checks.append(failed("model names unique", f"{len(dupes)} duplicated: {dupes[:5]}")
                  if dupes else passed("model names unique", f"{len(stems)} distinct"))

    reserved = sorted({f.stem for f in (c.transform / "macros").rglob("*.sql")}
                      & set(RESERVED_MACROS))
    checks.append(failed("no dbt built-ins overridden", ", ".join(reserved))
                  if reserved else passed("no dbt built-ins overridden",
                                          "generate_schema_name, ref, source intact"))
    return checks


# ================================================================ ontology ==
def _raw_resources(c: Ctx) -> set[str]:
    """Every raw table the project loads, from seeds and declared dbt sources.

    These are what annotations attach to. Models are not raw and are deliberately
    excluded — annotating a mart would assert that a derived table is a source of
    record, which is how a definition ends up with two homes.
    """
    names = {f.stem for f in (c.transform / "seeds").rglob("*.csv")}
    for f in (c.transform / "models").rglob("*.yml"):
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if not isinstance(doc, dict):
            continue
        for src in doc.get("sources") or []:
            for tbl in (src or {}).get("tables") or []:
                if isinstance(tbl, dict) and tbl.get("name"):
                    names.add(str(tbl["name"]))
    return names


def eval_ontology(c: Ctx) -> list[Risk]:
    from pf.ontology.model import load_group_ontology
    from pf.ontology.validate import validate_sources, validate_topology

    out: list[Risk] = []
    anns = c.annotations
    if not anns:
        return [Risk("no-annotations", "blocks",
                     "contracts/annotations.yaml is missing or empty",
                     "Nothing downstream has meaning without it: generated "
                     "staging, the knowledge graph, PII policy and the metric "
                     "layer all read the roles. Annotate every raw resource, "
                     "then `pf check`.")]

    onto = load_group_ontology(c.root, c.group)
    issues = [i for i in validate_sources(anns, onto) if i.severity == "error"]
    by_rule = Counter(i.rule for i in issues)
    if issues:
        unknown = sorted({i.message.split("'")[1] for i in issues
                          if i.rule in ("unknown-class", "unknown-link-target")})
        remedy = ("Fix the annotation where the concept is wrong. Where the "
                  "concept is right and this ontology has no word for it, that "
                  "is an ontology gap, not an annotation bug: "
                  f"`pf semantic scan {c.group} {c.project}` induces a proposal, "
                  f"`pf semantic review` shows what it would change, and "
                  f"`pf semantic approve` merges it into the group extension.")
        if unknown:
            remedy = f"Missing concept(s): {', '.join(unknown)}. " + remedy
        out.append(Risk("annotation-invalid", "blocks",
                        f"{len(issues)} error(s) against the ontology: {_fmt(by_rule)}",
                        remedy))

    topo = [i for i in validate_topology(onto) if i.severity == "error"]
    if topo:
        out.append(Risk("topology-invalid", "blocks",
                        f"{len(topo)} topology error(s): "
                        f"{'; '.join(str(i) for i in topo[:3])}",
                        "A relation whose domain or range is not a class cannot "
                        "be projected into MDL or OWL, and the link validation "
                        "above silently passes anything it cannot resolve."))

    raw = _raw_resources(c)
    annotated = {a.resource for a in anns}
    gap = sorted(raw - annotated - set(c.unmodelled))
    if gap:
        out.append(Risk("resource-unannotated", "blocks",
                        f"{len(gap)} raw resource(s) carry no annotation: "
                        f"{', '.join(gap[:8])}"
                        f"{f' +{len(gap) - 8} more' if len(gap) > 8 else ''}",
                        "An unannotated source has no concept, so no role-driven "
                        "cleaning, no PII policy and no place in the graph. "
                        "Annotate it — or, if it is a junction table or technical "
                        "exhaust rather than an entity, list it under "
                        "`unmodelled:` in annotations.yaml with the reason."))

    stray = sorted(annotated - raw)
    if stray:
        out.append(Risk("annotation-orphaned", "decide",
                        f"{len(stray)} annotation(s) name nothing that exists: "
                        f"{', '.join(stray[:8])}",
                        "Either the resource was renamed and the annotation was "
                        "not, or the annotation is left over from the source "
                        "repository. Both are worth knowing before `pf gen-staging`."))
    return out


def check_ontology(c: Ctx) -> list[Check]:
    from pf.ontology.model import load_group_ontology
    from pf.ontology.validate import validate_sources, validate_topology

    anns = c.annotations
    if not anns:
        return [failed("annotations present", "contracts/annotations.yaml empty or missing")]

    onto = load_group_ontology(c.root, c.group)
    checks = [passed("annotations present", f"{len(anns)} resource(s) annotated")]

    errors = [i for i in validate_sources(anns, onto) if i.severity == "error"]
    checks.append(failed("annotations conform", f"{len(errors)} error(s): "
                         f"{_fmt(Counter(i.rule for i in errors))}")
                  if errors else
                  passed("annotations conform", "no ontology errors"))

    topo = [i for i in validate_topology(onto) if i.severity == "error"]
    checks.append(failed("topology conforms", f"{len(topo)} error(s)")
                  if topo else passed("topology conforms",
                                      f"{len(onto.relations)} relation(s) resolve"))

    raw = _raw_resources(c)
    gap = sorted(raw - {a.resource for a in anns} - set(c.unmodelled))
    note = f", {len(c.unmodelled)} recorded as unmodelled" if c.unmodelled else ""
    checks.append(failed("every raw resource accounted for",
                         f"{len(gap)} neither annotated nor recorded: {gap[:5]}")
                  if gap else
                  passed("every raw resource accounted for",
                         f"{len(raw)} resource(s){note}"))
    return checks


# ================================================================= dialect ==
def _target_type(c: Ctx, target: str) -> str | None:
    block = c.outputs.get(target)
    return (block or {}).get("type") if isinstance(block, dict) else None


def eval_dialect(c: Ctx) -> list[Risk]:
    from pf.onboard.dialect import AMBIGUOUS, TOOLKITS

    out: list[Risk] = []
    r = c.dialect

    if r.unsupported:
        out.append(Risk("sql-unsupported", "blocks",
                        f"{len(r.unsupported)} function(s) no adapter here can "
                        f"resolve and no toolkit macro covers: {_fmt(r.unsupported)}",
                        "Port these call sites, or add a macro to "
                        "platform/toolkits/dbt-snowflake/macros/ and register it "
                        "in pf/onboard/dialect.py."))
    if r.covered:
        pairs = ", ".join(f"{n} -> {{{{ {r.macro_for(n)}(...) }}}}"
                          for n, _ in r.covered.most_common(4))
        out.append(Risk("sql-needs-wrapping", "blocks",
                        f"{sum(r.covered.values())} call site(s) across "
                        f"{len(r.covered)} function(s) the dev adapter cannot "
                        f"resolve: {_fmt(r.covered)}",
                        f"Each has a portable macro: {pairs}. Wrapping them is "
                        f"what makes one model run on DuckDB and Snowflake both."))
    if r.ambiguous:
        out.append(Risk("sql-ambiguous", "blocks",
                        f"{len(r.ambiguous)} function(s) both adapters resolve and "
                        f"disagree about: {_fmt(r.ambiguous)}",
                        "These compile on dev and return different values in "
                        "production — nothing announces it. Wrap each in its "
                        "`sf_*` macro, which pins one semantics on every adapter. "
                        + "; ".join(f"{n} - {AMBIGUOUS[n]}"
                                    for n in list(r.ambiguous)[:2])))

    for target, want in TARGET_TYPES.items():
        have = _target_type(c, target)
        if have is None:
            out.append(Risk("target-missing", "blocks",
                            f"profiles.yml declares no `{target}` target",
                            f"The ladder expects dev and base on DuckDB (a "
                            f"laptop build with no credentials, and a base "
                            f"schema for Recce to diff against) and prod on the "
                            f"warehouse the business runs. Add it, or "
                            f"`pf capability-add {c.group} {c.project} snowflake`."))
        elif want and have != want:
            out.append(Risk("target-wrong-type", "blocks",
                            f"target `{target}` is type `{have}`, expected `{want}`",
                            "Development has to run without credentials or it "
                            "stops being run at all."))

    if _target_type(c, "prod") == "duckdb":
        out.append(Risk("prod-not-declared", "decide",
                        "prod is still DuckDB — the scaffold default, not a decision",
                        f"If production really is DuckDB, say so in decisions/ and "
                        f"this stops being a finding. Otherwise "
                        f"`pf capability-add {c.group} {c.project} snowflake` "
                        f"writes the prod target from environment variables; no "
                        f"credential is read or stored here."))

    paths = c.dbt_config.get("macro-paths") or []
    for tk in TOOLKITS:
        if not any(tk in str(p) for p in paths):
            out.append(Risk("toolkit-unwired", "blocks",
                            f"macro-paths does not include the {tk} toolkit",
                            f"The `sf_*` macros are not on the path, so every "
                            f"wrapped call site fails to compile. Add "
                            f"`../../../../../platform/toolkits/{tk}/macros`."))
    return out


def check_dialect(c: Ctx) -> list[Check]:
    from pf.onboard.dialect import TOOLKITS

    r = c.dialect
    checks = [
        passed("no unresolvable functions", f"{len(r.calls)} distinct call(s) scanned")
        if not r.unsupported and not r.covered else
        failed("no unresolvable functions",
               f"{_fmt(r.unsupported + r.covered)}"),
        passed("no dialect-ambiguous functions", "every call means one thing on both adapters")
        if not r.ambiguous else
        failed("no dialect-ambiguous functions", _fmt(r.ambiguous)),
    ]

    for target, want in TARGET_TYPES.items():
        have = _target_type(c, target)
        if have is None:
            checks.append(failed(f"target `{target}` declared", "absent from profiles.yml"))
        elif want and have != want:
            checks.append(failed(f"target `{target}` declared", f"type `{have}`, expected `{want}`"))
        else:
            checks.append(passed(f"target `{target}` declared", f"type `{have}`"))

    paths = [str(p) for p in (c.dbt_config.get("macro-paths") or [])]
    missing = [t for t in TOOLKITS if not any(t in p for p in paths)]
    checks.append(failed("portable macros on macro-paths", f"missing: {', '.join(missing)}")
                  if missing else
                  passed("portable macros on macro-paths", ", ".join(TOOLKITS)))

    checks.append(_parse_check(c))
    return checks


def _parse_check(c: Ctx) -> Check:
    """`dbt parse` against dev — the cheapest proof the whole project compiles."""
    if shutil.which("dbt") is None:
        return unexercised("dbt parse (dev)", "dbt is not on PATH")
    proc = c.dbt("parse")
    if proc.returncode == 0:
        return passed("dbt parse (dev)", "manifest built")
    tail = [ln for ln in (proc.stdout + proc.stderr).splitlines() if ln.strip()][-3:]
    return failed("dbt parse (dev)", " / ".join(tail)[:400])


# ================================================================== layers ==
def eval_layers(c: Ctx) -> list[Risk]:
    out: list[Risk] = []

    stray = sorted(set(c.models) - set(LAYERS))
    if stray:
        counts = Counter({k: len(c.models[k]) for k in stray})
        out.append(Risk("layer-foreign", "blocks",
                        f"{sum(counts.values())} model(s) sit in director(y/ies) "
                        f"this platform does not know: {_fmt(counts)}",
                        f"Every model belongs to exactly one of {', '.join(LAYERS)}. "
                        f"An `intermediate/` directory is the usual case: those "
                        f"models are marts that nothing exposes yet, so move them "
                        f"under marts/ and let tags carry the distinction."))

    configured = ((c.dbt_config.get("models") or {})
                  .get(c.project.replace("-", "_")) or {})
    for layer in CONFIGURED_LAYERS:
        if c.models.get(layer) and layer not in configured:
            out.append(Risk("layer-unconfigured", "blocks",
                            f"`{layer}` holds {len(c.models[layer])} model(s) and "
                            f"has no block in dbt_project.yml",
                            "Without one they build with dbt's defaults instead of "
                            "this platform's materialisation and schema, and the "
                            "layer separation the knowledge graph reads stops "
                            "existing."))

    joined = [f for f in c.models.get("staging", []) if len(_upstreams(f)) > 1]
    if joined:
        out.append(Risk("staging-not-1to1", "blocks",
                        f"{len(joined)} staging model(s) read more than one "
                        f"upstream: {', '.join(f.stem for f in joined[:6])}"
                        f"{f' +{len(joined) - 6} more' if len(joined) > 6 else ''}",
                        "Staging is 1:1 with a raw table — renaming, casting and "
                        "cleaning only. A join in staging hides a business "
                        "decision in a layer the platform treats as mechanical, "
                        "and `pf gen-staging` will overwrite it. Move them to "
                        "marts/."))

    unlisted = sorted(f.stem for f in c.models.get("", []))
    if unlisted:
        out.append(Risk("layer-none", "decide",
                        f"{len(unlisted)} model(s) sit directly in models/ with no "
                        f"layer: {', '.join(unlisted[:6])}",
                        "A model with no layer is invisible to every rule keyed on "
                        "one. Put each in staging/, marts/ or utils/."))
    return out


def check_layers(c: Ctx) -> list[Check]:
    stray = sorted(set(c.models) - set(LAYERS))
    checks = [
        failed("every model in a known layer",
               f"foreign: {', '.join(stray)}") if stray else
        passed("every model in a known layer",
               ", ".join(f"{k}={len(v)}" for k, v in sorted(c.models.items()))),
    ]

    configured = ((c.dbt_config.get("models") or {})
                  .get(c.project.replace("-", "_")) or {})
    missing = [x for x in CONFIGURED_LAYERS if c.models.get(x) and x not in configured]
    checks.append(failed("populated layers configured", f"no config for: {', '.join(missing)}")
                  if missing else
                  passed("populated layers configured",
                         ", ".join(x for x in CONFIGURED_LAYERS if x in configured) or "none needed"))

    joined = [f.stem for f in c.models.get("staging", []) if len(_upstreams(f)) > 1]
    checks.append(failed("staging is 1:1 with raw", f"{len(joined)} join: {joined[:5]}")
                  if joined else
                  passed("staging is 1:1 with raw",
                         f"{len(c.models.get('staging', []))} model(s), one upstream each"))
    return checks


# ================================================================= metrics ==
def _semantic_counts(c: Ctx) -> tuple[list[str], list[dict]]:
    models: list[str] = []
    metrics: list[dict] = []
    for doc in c.semantic_yaml:
        models += [m.get("name", "?") for m in (doc.get("semantic_models") or [])]
        metrics += [m for m in (doc.get("metrics") or []) if isinstance(m, dict)]
    return models, metrics


def eval_metrics(c: Ctx) -> list[Risk]:
    out: list[Risk] = []
    sem, metrics = _semantic_counts(c)
    marts = c.models.get("marts", [])

    if not sem:
        out.append(Risk("no-semantic-models", "blocks",
                        f"{len(marts)} mart(s) and no semantic model",
                        "A mart nothing measures is a table, not a metric. "
                        "Declare a semantic model per mart that carries a grain: "
                        "entities from the annotated keys, dimensions from the "
                        "roles, measures from the money and count columns."))
    if not metrics:
        out.append(Risk("no-metrics", "blocks", "no metric is defined",
                        "Until one exists every business question falls back to "
                        "ad-hoc SQL, which is how one company ends up with two "
                        "revenues. Start with the figures the source repository's "
                        "own reports already computed."))

    measured = {m.get("model", "").strip() for m in
                (x for doc in c.semantic_yaml for x in (doc.get("semantic_models") or []))}
    measured = {re.sub(r"^ref\(['\"]|['\"]\)$", "", m) for m in measured}
    uncovered = [f.stem for f in marts if f.stem not in measured]
    if marts and uncovered:
        out.append(Risk("mart-uncovered", "decide",
                        f"{len(uncovered)} of {len(marts)} mart(s) have no semantic "
                        f"model: {', '.join(uncovered[:6])}"
                        f"{f' +{len(uncovered) - 6} more' if len(uncovered) > 6 else ''}",
                        "Full coverage is rarely the goal — most marts are "
                        "intermediate. Cover the ones a person asks questions "
                        "about, and say in decisions/ why the rest are not."))

    undescribed = [m.get("name", "?") for m in metrics if not m.get("description")]
    if undescribed:
        out.append(Risk("metric-undescribed", "decide",
                        f"{len(undescribed)} metric(s) carry no description: "
                        f"{', '.join(undescribed[:6])}",
                        "The description is the definition an agent quotes when "
                        "it answers. Without one the metric is a name and a sum."))

    spine = (c.transform / "models" / "utils" / "metricflow_time_spine.sql")
    if metrics and not spine.exists():
        out.append(Risk("no-time-spine", "blocks",
                        "metrics are defined but there is no metricflow_time_spine model",
                        "Cumulative, derived and offset metrics all need it; "
                        "without one they fail at query time rather than at parse."))
    return out


def check_metrics(c: Ctx) -> list[Check]:
    sem, metrics = _semantic_counts(c)
    checks = [
        passed("semantic models declared", f"{len(sem)}: {', '.join(sem[:5])}")
        if sem else failed("semantic models declared", "none found under models/semantic"),
        passed("metrics declared", f"{len(metrics)}: "
               f"{', '.join(m.get('name', '?') for m in metrics[:5])}")
        if metrics else failed("metrics declared", "none found"),
    ]

    if shutil.which("dbt") is None:
        checks.append(unexercised("semantic manifest validates", "dbt is not on PATH"))
    else:
        proc = c.dbt("parse")
        if proc.returncode != 0:
            tail = [ln for ln in (proc.stdout + proc.stderr).splitlines() if ln.strip()][-3:]
            checks.append(failed("semantic manifest validates", " / ".join(tail)[:400]))
        else:
            mf = c.transform / "target" / "semantic_manifest.json"
            if mf.exists():
                doc = json.loads(mf.read_text(encoding="utf-8"))
                checks.append(passed(
                    "semantic manifest validates",
                    f"{len(doc.get('semantic_models') or [])} semantic model(s), "
                    f"{len(doc.get('metrics') or [])} metric(s) accepted by dbt"))
            else:
                checks.append(failed("semantic manifest validates",
                                     "dbt parsed but wrote no semantic_manifest.json"))

    if shutil.which("mf") is None:
        checks.append(unexercised(
            "a metric answers a query",
            "the MetricFlow CLI is not installed — `uv add dbt-metricflow`. "
            "Parsing proves the definitions are well-formed, not that they run."))
    elif not metrics:
        checks.append(unexercised("a metric answers a query", "no metric to query"))
    else:
        import os

        name = metrics[0].get("name", "")
        # MetricFlow resolves the warehouse through dbt's own profile, so it needs
        # the same three environment variables `pf` passes to dbt. Without
        # DBT_PROFILES_DIR it looks in ~/.dbt and reports a missing profile,
        # which reads as a broken metric rather than a missing variable.
        env = dict(os.environ, DBT_TARGET="dev",
                   DBT_PROFILES_DIR=str(c.transform),
                   PF_DUCKDB_PATH=str(c.duckdb_path))
        proc = subprocess.run(
            ["mf", "query", "--metrics", name, "--limit", "1"],
            cwd=str(c.transform), env=env, capture_output=True, text=True, check=False)
        out = (proc.stderr or proc.stdout).strip()
        checks.append(
            passed("a metric answers a query", f"`mf query --metrics {name}` returned rows")
            if proc.returncode == 0 else
            failed("a metric answers a query",
                   out.splitlines()[-1][:300] if out else "non-zero exit"))
    return checks


# ================================================================== review ==
def _manifest_at(c: Ctx, target_dir: str) -> Path:
    return c.transform / target_dir / "manifest.json"


def eval_review(c: Ctx) -> list[Risk]:
    out: list[Risk] = []
    base, current = _manifest_at(c, "target-base"), _manifest_at(c, "target")

    if not current.exists():
        out.append(Risk("no-current-manifest", "blocks",
                        "transform/target/manifest.json does not exist",
                        "Nothing has been built or parsed. Run `pf seed "
                        f"{c.group} {c.project}`."))
    if not base.exists():
        out.append(Risk("no-base-manifest", "blocks",
                        "transform/target-base/manifest.json does not exist",
                        "Recce compares two states; without a base there is "
                        "nothing to compare to. Build the `base` target from the "
                        "last known-good revision — that is what the `base` "
                        "DuckDB schema exists for."))
    if shutil.which("recce") is None:
        out.append(Risk("recce-absent", "decide",
                        "the recce CLI is not installed",
                        "Lineage says what could break; only a diff says what "
                        "did. Without it this stage can check that the two "
                        "states exist and nothing about whether they agree."))

    if base.exists() and current.exists():
        try:
            b = set(json.loads(base.read_text(encoding="utf-8")).get("nodes", {}))
            n = set(json.loads(current.read_text(encoding="utf-8")).get("nodes", {}))
        except (json.JSONDecodeError, OSError):
            b = n = set()
        added, removed = n - b, b - n
        if added or removed:
            out.append(Risk("node-set-changed", "decide",
                            f"{len(added)} node(s) added and {len(removed)} removed "
                            f"since base",
                            "Expected during an onboarding — but every removal is "
                            "a model something downstream may still reference. "
                            "Check them against `pf impact` before accepting."))
    return out


def check_review(c: Ctx) -> list[Check]:
    base, current = _manifest_at(c, "target-base"), _manifest_at(c, "target")
    checks = [
        passed("current state built", str(current.relative_to(c.transform)))
        if current.exists() else failed("current state built", "no target/manifest.json"),
        passed("base state built", str(base.relative_to(c.transform)))
        if base.exists() else failed("base state built", "no target-base/manifest.json"),
    ]
    if shutil.which("recce") is None:
        checks.append(unexercised("recce diff clean",
                                  "recce is not on PATH — `uv add recce`"))
        return checks
    if not (base.exists() and current.exists()):
        checks.append(unexercised("recce diff clean", "needs both states"))
        return checks

    import os

    env = dict(os.environ, DBT_TARGET="dev", PF_DUCKDB_PATH=str(c.duckdb_path))
    proc = subprocess.run(
        ["recce", "run",
         "--project-dir", str(c.transform), "--profiles-dir", str(c.transform),
         "--target-path", str(c.transform / "target"),
         "--target-base-path", str(c.transform / "target-base"),
         "-o", str(c.transform / "target" / "recce_state.json")],
        cwd=str(c.transform), env=env, capture_output=True, text=True, check=False)
    if proc.returncode == 0:
        checks.append(passed("recce diff clean", "`recce run` completed with no failed check"))
    else:
        tail = [ln for ln in (proc.stdout + proc.stderr).splitlines() if ln.strip()][-2:]
        checks.append(failed("recce diff clean", " / ".join(tail)[:300]))
    return checks


# =================================================================== table ==
STAGES: tuple[Stage, ...] = (
    Stage("import", "Import", "the repository is here and is a dbt project this "
          "platform recognises",
          "references/stage-import.md", eval_import, check_import,
          owns=("transform/**", "src/**", "contracts/**", "decisions/**")),
    Stage("ontology", "Ontology, topology and annotations",
          "every raw resource has a concept, roles and links this ontology can "
          "validate",
          "references/stage-ontology.md", eval_ontology, check_ontology,
          owns=("contracts/**", "src/*/sources/**", "decisions/**"),
          token_budget=12_000),
    Stage("dialect", "One SQL, two targets",
          "the same models compile on DuckDB in development and on the production "
          "warehouse, and mean the same thing on both",
          "references/stage-dialect.md", eval_dialect, check_dialect,
          owns=("transform/models/**", "transform/macros/**", "transform/tests/**",
                "transform/snapshots/**", "transform/analyses/**",
                "transform/dbt_project.yml", "transform/profiles.yml",
                "docs/**", "decisions/**"),
          token_budget=20_000),
    Stage("layers", "Staging, marts, semantic",
          "every model sits in the layer whose rules it obeys",
          "references/stage-layers.md", eval_layers, check_layers,
          owns=("transform/models/**", "transform/dbt_project.yml", "decisions/**"),
          token_budget=16_000),
    Stage("metrics", "MetricFlow",
          "the business quantities have one definition each, and it runs",
          "references/stage-metrics.md", eval_metrics, check_metrics,
          owns=("transform/models/semantic/**", "transform/models/utils/**",
                "decisions/**"),
          token_budget=16_000),
    Stage("review", "Recce",
          "the difference between what was there and what is there now has been "
          "looked at",
          "references/stage-review.md", eval_review, check_review,
          owns=("transform/models/**", "decisions/**", "recce.yml"),
          token_budget=8_000),
)

BY_NAME = {s.name: s for s in STAGES}


# ================================================================= checker ==
#: Edits that make a gate pass without making anything true. Each is a real
#: shortcut someone reaches for when a stage will not close, and each is
#: detectable in a diff, which is the only reason these three are listed and
#: other forms of cheating are not.
_CHEATS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("test disabled", re.compile(r"^\+.*\+?enabled:\s*false", re.MULTILINE | re.IGNORECASE),
     "a model or test switched off rather than fixed"),
    ("severity lowered", re.compile(r"^\+.*severity:\s*warn", re.MULTILINE | re.IGNORECASE),
     "a failing test downgraded to a warning"),
    ("gate loosened", re.compile(r"^\+.*(?:maxFiles|denylist|blockOn)", re.MULTILINE),
     "the policy that judges the change, edited by the change"),
)


def changed(root: Path, pdir: Path) -> list[tuple[str, str]]:
    """(status, repo-relative path) for every uncommitted change in one project.

    The status code is kept rather than discarded because deletion is the one
    change whose *kind* matters more than its path: a deleted test and an edited
    test are the same path and opposite verdicts.
    """
    # `-uall`, because the default collapses an untracked directory into a single
    # entry ending in `/`. That made a 1,200-file import look like one change
    # whose path, once the project prefix was stripped, was the empty string —
    # so the scope check compared "" against every pattern and the size check
    # counted one file.
    proc = subprocess.run(
        ["git", "status", "--porcelain", "-uall", "--", str(pdir)],
        cwd=str(root), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return []
    out: list[tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        status, path = line[:2].strip(), line[3:].strip().strip('"')
        if " -> " in path:            # a rename reports both halves
            path = path.split(" -> ", 1)[1]
        if path:
            out.append((status or "?", path))
    return out


def _ever_committed(root: Path, pdir: Path) -> bool:
    proc = subprocess.run(["git", "ls-files", "--", str(pdir)],
                          cwd=str(root), capture_output=True, text=True, check=False)
    return proc.returncode == 0 and bool(proc.stdout.strip())


def _owned(rel: str, patterns: tuple[str, ...]) -> bool:
    from pf.loops.gate import _match

    return bool(_match(rel, list(patterns)))


def verify(c: Ctx, stage: Stage) -> list[Check]:
    """The checker half of a maker/checker split, run against the diff.

    `validate` asks whether the project is now correct. This asks the different
    question loop-engineering's verifier asks: whether the change that got it
    there is one we would accept. They catch different things — a change can pass
    every gate by deleting the test that was failing — and the split only works
    because this half is not written by whoever made the change.

    Deliberately mechanical and deliberately incomplete. It checks scope, size
    and three specific shortcuts. Intent — "does this address the finding rather
    than a different problem" — is not decidable here and is left to the skill,
    which says so rather than implying this covers it.
    """
    from pf.loops.gate import load_policy

    edits = changed(c.root, c.pdir)
    checks: list[Check] = []
    if not edits:
        return [unexercised("scope", "no uncommitted change in this project")]

    # Nothing about this project is committed, so every file in it is "changed"
    # and there is no way to tell this stage's work from the import that created
    # it. Saying so is the honest answer; failing the size check on a 1,200-file
    # import that was supposed to add 1,200 files is not.
    if not _ever_committed(c.root, c.pdir):
        checks.append(unexercised(
            "changes stay in scope",
            f"{len(edits)} file(s), none committed yet — commit the import so a "
            f"stage's diff can be told apart from it"))
        checks.append(unexercised("change is reviewable", "no baseline to diff against"))
        checks.append(_comprehension_check(c, stage, [p for _, p in edits]))
        return checks

    paths = [p for _, p in edits]
    rel = [p.split(f"projects/{c.project}/", 1)[-1] for p in paths]
    outside = [r for r in rel if stage.owns and not _owned(r, stage.owns)]
    checks.append(failed("changes stay in scope",
                         f"{len(outside)} outside `{stage.name}`: {outside[:4]}")
                  if outside else
                  passed("changes stay in scope",
                         f"{len(rel)} file(s), all within {', '.join(stage.owns[:3])}"))

    limit = int(load_policy(c.root).get("maxFiles", 0) or 0)
    if not limit:
        checks.append(unexercised("change is reviewable", "gate.yaml sets no maxFiles"))
    elif len(paths) > limit:
        checks.append(failed("change is reviewable",
                             f"{len(paths)} files vs maxFiles {limit} — split it, "
                             f"or say in decisions/ why this one is mechanical"))
    else:
        checks.append(passed("change is reviewable", f"{len(paths)} of {limit} files"))

    diff = subprocess.run(["git", "diff", "--unified=0", "--", str(c.pdir)],
                          cwd=str(c.root), capture_output=True, text=True, check=False).stdout
    hits = [(name, why) for name, pat, why in _CHEATS if pat.search(diff)]
    checks.append(failed("nothing was switched off",
                         "; ".join(f"{n} — {w}" for n, w in hits))
                  if hits else
                  passed("nothing was switched off",
                         "no test disabled, severity lowered or gate edited"))

    gone = [p for status, p in edits
            if "D" in status and ("/tests/" in p or "/data-tests/" in p
                                  or Path(p).name.startswith("test_"))]
    checks.append(failed("no test deleted", f"{len(gone)}: {gone[:3]}")
                  if gone else passed("no test deleted", "test files intact"))

    checks.append(_comprehension_check(c, stage, rel))
    return checks


def _comprehension_check(c: Ctx, stage: Stage, rel: list[str]) -> Check:
    """Whether the judgement calls in this change were written down anywhere.

    Loop engineering's second named failure mode is *comprehension debt*: code
    ships faster than understanding accumulates. It is the specific risk of
    onboarding, where a thousand models arrive at once and every one of them was
    understood by somebody who is not here. A loop that resolves a judgement call
    and leaves no trace of the reasoning has produced a working project nobody
    can maintain.

    So this is mechanical rather than exhortative. If the stage's evaluate raised
    findings graded `decide` — the ones where both choices are defensible — the
    change is expected to touch `decisions/`. Not because a file makes a decision
    good, but because a decision nobody wrote down is one the next person has to
    re-derive from the SQL.
    """
    open_calls = [r for r in stage.evaluate(c) if r.severity == "decide"]
    if not open_calls:
        return passed("judgement calls recorded", "none outstanding")
    if any(r.startswith("decisions/") for r in rel):
        return passed("judgement calls recorded",
                      f"{len(open_calls)} open, decisions/ updated")
    return failed("judgement calls recorded",
                  f"{len(open_calls)} finding(s) need a choice and nothing was "
                  f"written to decisions/: {', '.join(r.kind for r in open_calls[:3])}")


# ================================================================= breaker ==
def record(root: Path, group: str, project: str, stage: Stage,
           verdict: Verdict) -> tuple[bool, str]:
    """Append this validation to the loop ledger, and report the breaker.

    The three-attempt limit is the one rule that cannot live in prose. An agent
    that re-reads "max 3 attempts" at the start of every iteration has no way to
    know it is on the fourth — the count is not in the conversation, and a
    restart would reset it anyway. Counting it in the ledger is what turns
    "escalate after three" from an intention into a thing that happens.
    """
    import uuid

    from pf.loops.runner import CircuitBreaker, Ledger, LoopRun, _now

    spec = spec_for(stage)
    ledger = Ledger(root)
    run = LoopRun(
        run_id=str(uuid.uuid4())[:8], loop=spec.name, group=group, project=project,
        started_at=_now(),
        attempt=ledger.consecutive_failures(spec.name, project) + 1,
        outcome="ok" if verdict.open else "escalated",
        findings=[f"{c.name}: {c.evidence}" for c in verdict.failures],
        message=verdict.summary,
    )
    ledger.append(run)
    allowed, why = CircuitBreaker(ledger, spec, daily_budget=0).check(group, project)
    return allowed, why


def ladder(root: Path, group: str, project: str) -> list[tuple[Stage, Verdict]]:
    """Validate every stage in order, stopping at the first closed gate.

    Stops rather than continuing because the stages downstream of a failure
    report nonsense: a project whose SQL does not compile has no manifest, so
    the metric stage would report "no metrics" when the truth is "not yet
    knowable". Reporting a finding that a later fix will erase trains people to
    ignore the report.
    """
    c = Ctx(root=root, group=group, project=project)
    out: list[tuple[Stage, Verdict]] = []
    for stage in STAGES:
        verdict = Verdict(stage.name, stage.validate(c))
        out.append((stage, verdict))
        if not verdict.open:
            break
    return out


def current(root: Path, group: str, project: str) -> tuple[Stage, Verdict] | None:
    """The stage the project is on: the first that does not pass, or None."""
    rungs = ladder(root, group, project)
    for stage, verdict in rungs:
        if not verdict.open:
            return stage, verdict
    if rungs and len(rungs) == len(STAGES) and rungs[-1][1].open:
        return None
    return rungs[-1] if rungs else None


def state_entries(root: Path, group: str, project: str) -> list[str]:
    """The ladder's position, as lines for STATE.md.

    A loop forgets everything between runs, so its memory has to be on disk. The
    verdicts themselves are deliberately *not* stored — a recorded pass outlives
    the change that invalidated it, which is worse than no record. What is worth
    writing down is the position and the open questions: where the ladder
    stopped, and what it stopped on. Both are re-derived here on every write, so
    the file can be stale but can never be wrong in a way that survives a
    re-read.
    """
    rungs = ladder(root, group, project)
    done = [s.name for s, v in rungs if v.open]
    out = [(f"{group}/{project}: onboarding at stage "
            f"`{rungs[-1][0].name}` ({len(done)}/{len(STAGES)} open) — "
            f"{rungs[-1][1].summary}")]
    for stage, verdict in rungs:
        for c in verdict.failures:
            out.append(f"{group}/{project} [{stage.name}] {c.name}: {c.evidence}")
        for c in verdict.gaps:
            out.append(f"{group}/{project} [{stage.name}] not exercised — {c.evidence}")
    return out


def spec_for(stage: Stage) -> object:
    """A `LoopSpec` for driving one stage through the loop runner.

    Deliberately not registered in `pf.loops.registry`: those are cadence loops
    that `pf loop run-all` executes against every project, and an aligned project
    reporting "no ontology proposal" every day forever would train everyone to
    ignore the whole report. The ladder is invoked, not scheduled — but it still
    wants the runner's ledger, attempt count and circuit breaker, so it borrows
    the spec type rather than the catalogue.
    """
    from pf.loops.runner import LoopSpec

    return LoopSpec(
        name=f"onboard-{stage.name}",
        description=stage.subject,
        autonomy="L1",
        cadence="on demand",
        token_budget=stage.token_budget,
        writes=False,
    )
