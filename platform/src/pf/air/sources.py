"""Where a control catalogue comes from, and how to read it.

`pf.air` is not a FINOS reader. It is a reader of *control catalogues*, and FINOS
is the one this repository happens to pin. The distinction matters because the
next catalogue is not hypothetical: a tenant with a sector regulator, a company
with its own control library, NIST AI RMF, or a second framework carried
alongside the first — none of which should require editing the parser.

So a catalogue is a **declaration**, and adding one is a `CatalogueSource` object:

    pf.air.sources.BUILTIN            in this repository
    [project.entry-points."pf.catalogues"]   in any installed distribution

which is the same seam, and the same reasoning, as `pf.tools`. Nothing in
`catalogue.py`, `coverage.py`, `register.py` or the CLI names a framework.

## What a source has to declare

Two things vary between catalogues and everything else follows from them:

**Where the documents are.** `Layout` — the directories holding risks, controls
and crosswalks, relative to the corpus root.

**What the frontmatter is called.** `Frontmatter` — the keys a document uses.
Defaults match the Jekyll-collection convention FINOS uses (`sequence`, `type`,
`doc-status`, `mitigates`, `<regime>_references`), because that convention is
common enough to be worth a default, not because it is the only one.

## Identity

A control's public id is derived, never stored: `id_template` rendered against
the source prefix, the document's type and its sequence. FINOS publishes
`AIR-DET-21` and that is what this produces.

**Prefixes must be unique across enabled sources**, because ids are the vocabulary
an `air.yaml` baseline speaks and a collision would silently re-point a
commitment at somebody else's control. `discover()` refuses to return two sources
sharing one, which is a loud failure at startup rather than a quiet one in a gate.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path

#: Entry-point group any installed distribution can contribute a catalogue on.
#: Mirrors `pf.tools.registry.ENTRY_POINT_GROUP`; see that module for why the
#: value is resolved lazily and a broken plugin degrades to a row rather than a
#: traceback.
ENTRY_POINT_GROUP = "pf.catalogues"


class InvalidSource(ValueError):
    """A catalogue declaration that could not be used. Raised at discovery."""


@dataclass(frozen=True)
class Layout:
    """Where the documents live, relative to the corpus root."""

    risks: str = "docs/_risks"
    controls: str = "docs/_mitigations"
    references: str = "docs/_data/references"
    #: Glob for a risk or control document.
    documents: str = "*.md"
    #: Glob for a crosswalk file.
    references_glob: str = "*.yml"


@dataclass(frozen=True)
class Frontmatter:
    """What the frontmatter keys are called.

    Defaults follow the Jekyll-collection convention. A catalogue that names its
    fields differently overrides the two or three that differ rather than
    reimplementing a parser.
    """

    sequence: str = "sequence"
    type: str = "type"
    title: str = "title"
    status: str = "doc-status"
    #: On a control: the risks it addresses, by document slug.
    mitigates: str = "mitigates"
    #: Sibling links, one key per document kind.
    related_risks: str = "related_risks"
    related_controls: str = "related_mitigations"
    #: A key ending in this names a crosswalk file: `eu-ai-act_references` ->
    #: `<references>/eu-ai-act.yml`.
    reference_suffix: str = "_references"
    #: `mi-21_agent-decision-audit.md` -> slug `mi-21`.
    slug_separator: str = "_"


@dataclass(frozen=True)
class CatalogueSource:
    """One control catalogue: where it is, how to read it, what it is called."""

    #: Stable key. `pf air catalogues` lists it; `air.yaml` never names it,
    #: because a baseline speaks in control ids and those already carry a prefix.
    name: str
    title: str
    #: Corpus root, relative to the repository root. Usually a `vendor/` submodule.
    path: str
    #: Id prefix. Must be unique across enabled sources.
    prefix: str
    url: str = ""
    licence: str = ""
    #: The credit line a *derived artefact* must carry, if the licence requires
    #: attribution. Empty means none is required — a permissive or in-house
    #: catalogue. `pf.air.register` emits every non-empty one it drew from, so
    #: an obligation cannot be dropped by forgetting to template it.
    attribution: str = ""
    layout: Layout = field(default_factory=Layout)
    frontmatter: Frontmatter = field(default_factory=Frontmatter)
    #: Rendered with `prefix`, `type` and `sequence`.
    id_template: str = "{prefix}-{type}-{sequence}"
    #: Type code -> human label. Empty means any code is accepted, which is the
    #: honest default for a catalogue whose vocabulary we have not been told.
    risk_types: Mapping[str, str] = field(default_factory=dict)
    control_types: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name or not self.prefix:
            raise InvalidSource("a catalogue source needs a name and an id prefix")
        try:
            self.id_for("X", 1)
        except KeyError as exc:
            raise InvalidSource(
                f"{self.name}: id_template {self.id_template!r} names {exc}, but only "
                f"prefix, type and sequence are available"
            ) from exc

    # -- identity ------------------------------------------------------------
    def id_for(self, doc_type: str, sequence: int | str) -> str:
        return self.id_template.format(
            prefix=self.prefix, type=str(doc_type).upper(), sequence=sequence)

    def owns(self, doc_id: str) -> bool:
        return doc_id.strip().upper().startswith(f"{self.prefix.upper()}-")

    # -- location ------------------------------------------------------------
    def root(self, repo: Path | str) -> Path:
        return Path(repo) / self.path

    def available(self, repo: Path | str) -> bool:
        """True when the corpus is on disk. A submodule nobody initialised is
        not an error — see `pf.air.catalogue.absent_reason`."""
        base = self.root(repo)
        return (base / self.layout.risks).is_dir() and (base / self.layout.controls).is_dir()

    def label_risk(self, code: str) -> str:
        return self.risk_types.get(code, code)

    def label_control(self, code: str) -> str:
        return self.control_types.get(code, code)

    def with_path(self, path: str) -> CatalogueSource:
        """The same catalogue read from somewhere else — used by tests and by a
        corpus vendored at a non-default location."""
        return replace(self, path=path)


# --------------------------------------------------------------- built-ins --
#: The FINOS AI Governance Framework, pinned at `vendor/ai-governance-framework`.
#:
#: Everything framework-specific in `pf.air` is in this object. The type
#: vocabularies are copied from upstream's `_config.yml` rather than read from it
#: — they are five literals, and depending on a Jekyll config at runtime to learn
#: an enum is the site-generator dependency the vendor registry declines.
#:
#: `RESP` is declared in upstream's `mi-template.md` and used by nothing yet. It
#: is admitted so the first response control to land upstream parses instead of
#: failing the build.
FINOS_AIR = CatalogueSource(
    name="finos-air",
    title="FINOS AI Governance Framework",
    path="vendor/ai-governance-framework",
    prefix="AIR",
    url="https://github.com/finos/ai-governance-framework",
    licence="CC-BY-4.0",
    attribution=(
        "Derived from the [FINOS AI Governance Framework]"
        "(https://github.com/finos/ai-governance-framework), "
        "© FINOS, licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). "
        "Risk and control definitions are quoted and summarised; the coverage "
        "assessment, control-to-policy mapping and all verdicts are this platform's "
        "own additions. Changes were made."
    ),
    risk_types={
        "RC": "Regulatory & Compliance",
        "OP": "Operational",
        "SEC": "Security",
    },
    control_types={
        "PREV": "Preventative",
        "DET": "Detective",
        "RESP": "Response",
    },
)

BUILTIN: tuple[CatalogueSource, ...] = (FINOS_AIR,)


# --------------------------------------------------------------- discovery --
@dataclass(frozen=True)
class DiscoveryError:
    """A catalogue that failed to load. Reported as a row, never as a traceback."""

    source: str
    error: str


def discover() -> tuple[dict[str, CatalogueSource], list[DiscoveryError]]:
    """Built-ins, then entry points. Later registrations never silently win.

    A duplicate `name` or a duplicate `prefix` is refused rather than resolved:
    two catalogues claiming `AIR-` would make an `air.yaml` baseline ambiguous,
    and a baseline that gates a control nobody meant is worse than one that
    fails to load.
    """
    found: dict[str, CatalogueSource] = {}
    prefixes: dict[str, str] = {}
    errors: list[DiscoveryError] = []

    def _add(src: CatalogueSource, origin: str) -> None:
        if src.name in found:
            errors.append(DiscoveryError(origin, f"duplicate catalogue name {src.name!r}"))
            return
        key = src.prefix.upper()
        if key in prefixes:
            errors.append(DiscoveryError(
                origin,
                f"prefix {src.prefix!r} already claimed by {prefixes[key]!r} — control "
                f"ids would be ambiguous"))
            return
        found[src.name] = src
        prefixes[key] = src.name

    for src in BUILTIN:
        _add(src, f"builtin:{src.name}")

    try:
        from importlib.metadata import entry_points

        eps = entry_points(group=ENTRY_POINT_GROUP)
    except Exception as exc:  # noqa: BLE001 — a broken environment is a row, not a crash
        errors.append(DiscoveryError(ENTRY_POINT_GROUP, str(exc)))
        return found, errors

    for ep in eps:
        try:
            obj = ep.load()
            for src in _coerce(obj):
                _add(src, ep.value)
        except Exception as exc:  # noqa: BLE001
            errors.append(DiscoveryError(ep.value, f"{type(exc).__name__}: {exc}"))
    return found, errors


def _coerce(obj: object) -> list[CatalogueSource]:
    """An entry point may resolve to a source, a factory, or an iterable of them."""
    if isinstance(obj, CatalogueSource):
        return [obj]
    if callable(obj):
        return _coerce(obj())
    if isinstance(obj, (list, tuple, set)):
        out: list[CatalogueSource] = []
        for item in obj:
            out.extend(_coerce(item))
        return out
    raise InvalidSource(f"expected a CatalogueSource, got {type(obj).__name__}")


def all_sources() -> dict[str, CatalogueSource]:
    return discover()[0]


def get(name: str) -> CatalogueSource:
    sources, errors = discover()
    if name in sources:
        return sources[name]
    broken = next((e for e in errors if e.source.endswith(name)), None)
    if broken:
        raise InvalidSource(f"{name}: {broken.error}")
    raise KeyError(f"unknown catalogue {name!r}; known: {', '.join(sorted(sources)) or 'none'}")


def available_sources(repo: Path | str) -> list[CatalogueSource]:
    """Every registered catalogue whose corpus is actually on disk."""
    return [s for s in all_sources().values() if s.available(repo)]


def source_for(doc_id: str) -> CatalogueSource | None:
    """Which catalogue an id belongs to, by prefix."""
    return next((s for s in all_sources().values() if s.owns(doc_id)), None)
