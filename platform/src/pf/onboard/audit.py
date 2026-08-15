"""What is risky about importing a given repository, and what to do about it.

`survey` observes and decides nothing. This module decides, and is kept separate
for that reason: the observations are facts about a repository, while everything
here is a judgement about *this* platform — its layer layout, its token budgets,
its gate. Splitting them means the judgements can change without the facts having
to be re-derived, and it keeps the honest-observation contract in `survey`
enforceable.

Severity is about what goes wrong if the risk is ignored, not about how hard it
is to fix:

``blocks``  the build fails, or succeeds while being wrong. Never auto-resolved.
``decide``  a human has to choose; both choices are defensible.
``note``    worth knowing, no action required.

The distinction that matters most is between a build that fails and a build that
is quietly wrong. A missing function stops dbt and someone fixes it in a minute.
A reversed `date_trunc` produces a warehouse full of plausible numbers, and that
is the one that reaches a dashboard.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import yaml

from pf.kg.card import ROLLUP_KEYS
from pf.onboard.dialect import AMBIGUOUS, Report, analyse
from pf.onboard.survey import RESERVED_MACROS, Survey

#: Layers the scaffolded dbt_project.yml configures. Anything else lands with no
#: materialisation or schema config at all.
CONFIGURED_LAYERS = frozenset({"staging", "marts"})

#: How many entries the context card names per section before rolling up. Kept
#: in step with `pf.kg.card._bullets`; a test pins them together.
_CARD_SECTION_LIMIT = 12


def _has_rollup_tags(s: Survey) -> bool:
    """Whether the source declares tags the card can group a large project by.

    Read from the incoming dbt_project.yml rather than from a built manifest,
    because the audit runs before anything is built.
    """
    text = str(s.dbt_config.get("models") or "")
    return any(f"{key}:" in text for key in ROLLUP_KEYS)


@dataclass(frozen=True)
class Risk:
    kind: str
    severity: str
    detail: str
    remedy: str

    @property
    def blocking(self) -> bool:
        return self.severity == "blocks"


_ORDER = {"blocks": 0, "decide": 1, "note": 2}


def audit(s: Survey, root: Path | None = None,
          dialect: Report | None = None) -> list[Risk]:
    """Every risk in importing this survey's repository, worst first."""
    risks: list[Risk] = []
    risks += _dialect_risks(s, dialect)
    risks += _macro_risks(s)
    risks += _collision_risks(s)
    risks += _package_risks(s)
    risks += _layout_risks(s)
    risks += _scale_risks(s, root)
    risks += _runtime_risks(s)
    return sorted(risks, key=lambda r: (_ORDER.get(r.severity, 9), r.kind))


def _fmt(counter: Counter, limit: int = 6) -> str:
    top = counter.most_common(limit)
    shown = ", ".join(f"{name} ×{n}" for name, n in top)
    rest = len(counter) - len(top)
    return f"{shown}{f', +{rest} more' if rest > 0 else ''}"


def _dialect_risks(s: Survey, report: Report | None) -> list[Risk]:
    if report is None:
        report = analyse(s.sql_files(), local_macros=set(s.macro_names))
    out: list[Risk] = []

    if report.unsupported:
        out.append(Risk(
            "sql-unsupported", "blocks",
            f"{len(report.unsupported)} function(s) the target cannot resolve "
            f"and no toolkit macro covers: {_fmt(report.unsupported)}",
            "Port these call sites by hand, or add a macro to "
            "platform/toolkits/dbt-snowflake/macros/ and register it in "
            "pf/onboard/dialect.py."))

    if report.covered:
        pairs = ", ".join(
            f"{n} -> {{{{ {report.macro_for(n)}(...) }}}}"
            for n, _ in report.covered.most_common(4))
        out.append(Risk(
            "sql-needs-wrapping", "blocks",
            f"{sum(report.covered.values())} call site(s) across "
            f"{len(report.covered)} function(s) the target cannot resolve: "
            f"{_fmt(report.covered)}",
            f"Each has a portable macro in the dbt-snowflake toolkit — wrap the "
            f"call sites and they compile on every adapter: {pairs}. The build "
            f"fails until then, which at least says so out loud."))

    if report.ambiguous:
        out.append(Risk(
            "sql-ambiguous", "blocks",
            f"{len(report.ambiguous)} function(s) the target resolves and means "
            f"something else by — different argument order or NULL handling: "
            f"{_fmt(report.ambiguous)}",
            "The worse half: these run without error and return wrong values, "
            "so nothing announces them. Wrap each in its `sf_*` macro, which "
            "pins the source dialect's semantics on every adapter. " + "; ".join(
                f"{n} — {AMBIGUOUS[n]}" for n in list(report.ambiguous)[:2])))
    return out


def _macro_risks(s: Survey) -> list[Risk]:
    return [
        Risk("reserved-macro", "blocks",
             f"the source overrides dbt's `{name}`, which {RESERVED_MACROS[name]}",
             f"Not imported. Re-add it to transform/macros/ only if you have "
             f"confirmed it agrees with this platform's layout "
             f"(original at {path.name}).")
        for name, path in sorted(s.reserved_macros.items())
    ]


def _collision_risks(s: Survey) -> list[Risk]:
    """dbt's model namespace is flat, so two `orders.sql` anywhere is fatal."""
    names = Counter(
        f.stem for files in s.models.values() for f in files if f.suffix == ".sql")
    dupes = {n: c for n, c in names.items() if c > 1}
    if not dupes:
        return []
    return [Risk(
        "name-collision", "blocks",
        f"{len(dupes)} model name(s) appear more than once across the layers "
        f"being merged: {_fmt(Counter(dupes))}",
        "dbt resolves models by bare name regardless of directory, so these "
        "must be renamed before the project will compile.")]


def _package_risks(s: Survey) -> list[Risk]:
    out: list[Risk] = []
    for key in s.unpinned_packages:
        out.append(Risk(
            "package-unpinned", "decide",
            f"package `{key}` follows a moving branch rather than a revision",
            "Every build resolves to whatever that branch is that day. Pin a "
            "revision, or drop the package if it is unused."))

    unused = [k for k, n in s.package_usage.items() if n == 0]
    if unused:
        out.append(Risk(
            "package-unused", "decide",
            f"no call sites found for: {', '.join(unused)}",
            "The namespace is guessed from the package name, so verify before "
            "removing — but a package with genuinely no uses is a dependency "
            "and a pin maintained for nothing."))
    return out


def _layout_risks(s: Survey) -> list[Risk]:
    out: list[Risk] = []
    if s.unmapped_layers:
        out.append(Risk(
            "layer-unmapped", "decide",
            f"unrecognised model directories {sorted(s.unmapped_layers)} were "
            f"placed under marts/",
            "Kept rather than dropped, and reported rather than guessed at. "
            "Move any that are really staging before `pf seed`, because the "
            "semantic layer will treat whatever is in marts/ as a mart."))

    stray = sorted(set(s.models) - CONFIGURED_LAYERS)
    if stray:
        out.append(Risk(
            "layer-unconfigured", "note",
            f"layer(s) {stray} have no entry in the scaffolded dbt_project.yml",
            "They will build with dbt's defaults rather than this platform's "
            "materialisation and schema settings. Add a block for them, or fold "
            "them into staging/marts."))
    return out


def _scale_risks(s: Survey, root: Path | None) -> list[Risk]:
    """Whether the platform's always-on contracts survive a project this size.

    Note what this deliberately does *not* claim. An earlier version computed the
    cost of listing every model and reported a budget overflow — which was wrong,
    because `pf kg card` truncates each section at a fixed limit and its output is
    therefore bounded regardless of project size. 772 marts render in the same 13
    lines as 100.

    The real cost of scale is not budget, it is density: a card that names 12 of
    772 marts is inside budget and nearly uninformative. `_summarise` in the card
    renderer rolls the remainder up by tag to recover that, which is only possible
    when the models carry `key:value` tags — so what is worth reporting here is
    whether they do.
    """
    out: list[Risk] = []
    names = [f.stem for files in s.models.values() for f in files
             if f.suffix == ".sql"]
    listed = _CARD_SECTION_LIMIT
    if len(names) > listed * 4:
        tagged = _has_rollup_tags(s)
        detail = (f"{len(names)} models; the context card names {listed} per "
                  f"section and rolls up the rest")
        out.append(Risk(
            "card-density", "note" if tagged else "decide",
            detail + (" by tag" if tagged else ", with no tags to roll up by"),
            "Card output is bounded, so the budget is safe either way."
            if tagged else
            "Without `domain:`/`type:` tags the card can only say how many were "
            "omitted, not what they are. Adding them to dbt_project.yml is the "
            "cheapest way to make a project this size legible to an agent."))

    if root is not None:
        gate = root / "gate.yaml"
        if gate.exists():
            try:
                max_files = (yaml.safe_load(gate.read_text()) or {}).get("maxFiles")
            except yaml.YAMLError:
                max_files = None
            if isinstance(max_files, int) and len(names) > max_files * 20:
                out.append(Risk(
                    "gate-maxfiles", "decide",
                    f"gate.yaml caps a loop run at {max_files} files; this "
                    f"project has {len(names)} models",
                    f"A single tag or column rename here touches far more than "
                    f"{max_files}, so a loop will hit the cap rather than finish. "
                    f"Loops are invoked per project, so the cheap answer is not "
                    f"to schedule them here — preferable to raising a global "
                    f"safety limit to suit one import."))
    return out


def _runtime_risks(s: Survey) -> list[Risk]:
    out: list[Risk] = []
    foreign = s.warehouses - {"duckdb", "motherduck"}
    if foreign:
        out.append(Risk(
            "warehouse-foreign", "note",
            f"the source profile targets {', '.join(sorted(foreign))}; each "
            f"project here gets its own DuckDB",
            "The profile is replaced, not ported. Whether the SQL survives the "
            "move is the sql-* findings above, not this one."))

    other = s.ingestion - {"dlt"}
    if other:
        out.append(Risk(
            "ingestion-foreign", "decide",
            f"ingestion via {', '.join(sorted(other))} is not replaced",
            "This platform expects annotated dlt sources. Static seed files are "
            "a fine interim answer; a live pipeline is not."))

    if s.dbt_project is None:
        out.append(Risk(
            "no-dbt-project", "blocks",
            "no dbt_project.yml found anywhere in the source",
            "Nothing will be imported and the knowledge graph has nothing to "
            "build from. Check the path, or the branch."))
    return out
