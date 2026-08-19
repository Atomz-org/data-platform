"""Reading a control catalogue — any control catalogue.

This module names no framework. Where the corpus is, what its frontmatter keys
are called, what its type codes mean and how its ids are formed all come from a
`CatalogueSource` (see `pf.air.sources`); this is the parser those declarations
drive. Adding a second catalogue is a `CatalogueSource`, not an edit here.

It reads exactly one thing from each document: the **YAML frontmatter**. The prose
body of a risk or a control is guidance written for a person — implementation
tiers, challenges, benefits — and parsing it would be inventing structure the
upstream does not claim to have. What an upstream *does* claim is its frontmatter
contract, and that is the surface we depend on.

## Ids are derived, not stored

`AIR-DET-21` is `id_template` rendered against the source's prefix and the
document's own `type` and `sequence`. The filename slug (`mi-21`) is kept because
that is what cross-references use — `mitigates: [ri-24]` — but it is not the
identity.

The consequence is worth stating: **a `type:` change upstream renames a control**,
and every `air.yaml` baseline naming the old id silently stops matching.
`pf air verify` exists for that, and it is why the vendor registry pins these
paths as `kind: data` rather than `reference`.

## Sequences are sparse

Entries get retired. Nothing here may assume a dense range or index by position.

## Absence is a state

A corpus is usually a submodule, so a clone without `--recurse-submodules` has an
empty directory rather than a catalogue. That is not an error — it is
`available()` returning False, and every caller reports `unexercised` rather than
raising, the same way `pf.tools.spec.Requirement` degrades a missing binary to
"not installed".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

import yaml

from pf.air.sources import (
    CatalogueSource,
    available_sources,
    source_for,
)


class NotVendored(RuntimeError):
    """No catalogue corpus is on disk. A state, not a corruption."""


class CorpusError(RuntimeError):
    """A corpus that does not honour its own frontmatter contract.

    Raised only from `pf.air.verify`; `load()` is tolerant so that one malformed
    document cannot take out `pf air show` for all the others.
    """


# ------------------------------------------------------------- frontmatter --
def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter, body). YAML between the first two `---` lines.

    Hand-split rather than regexed over the whole file because a `---` inside the
    prose body is an ordinary horizontal rule — these documents use them as
    section separators — and a greedy match would swallow the document.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            meta = yaml.safe_load("\n".join(lines[1:i])) or {}
            return (meta if isinstance(meta, dict) else {}), "\n".join(lines[i + 1 :])
    return {}, text


def _first_section(body: str) -> str:
    """The first paragraph under the first `##` heading.

    Matched by position rather than by name (`## Summary`, `## Purpose`,
    whatever this catalogue calls it), so a document that titles it differently
    still yields its opening paragraph instead of an empty string.
    """
    out: list[str] = []
    seen_heading = False
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("## "):
            if seen_heading:
                break
            seen_heading = True
            continue
        if not seen_heading:
            continue
        if not s:
            if out:
                break
            continue
        if s.startswith("---"):
            break
        out.append(s)
    return " ".join(out).strip()


# --------------------------------------------------------------- reference --
#: A citation key shaped like a *document* slug (`ri-2`, `mi-14`) rather than a
#: crosswalk key. Crosswalks key on the regulation's own numbering — `llm02-2025`,
#: `c3-s2-a10`, `au-2`, `A-8-3` — so a citation matching this is not a missing
#: entry. See `Reference.malformed`.
_SLUG_KEY = re.compile(r"^[a-z]{2}-\d+$")


@dataclass(frozen=True)
class Reference:
    """One citation into an external regime.

    `framework` is the crosswalk file's stem (`eu-ai-act`), `key` the stable
    identifier renaming which is a breaking change for whoever cites it.
    """

    framework: str
    key: str
    title: str
    url: str
    resolved: bool = True

    def __str__(self) -> str:
        return f"{self.title} [{self.framework}:{self.key}]"

    @property
    def malformed(self) -> bool:
        """True when this citation is an artefact of broken upstream frontmatter.

        A trailing `#` comment on the last item of a list can run into the
        following key with no newline —

            - ico-ai-data-protection-toolkit # ...in AI systemsrelated_risks:
              - ri-2

        — so YAML reads `related_risks:` as part of the comment and absorbs its
        items into the *previous* list. The document loses its sibling links and
        gains citations into a regulation that never mentioned it.

        Distinguished from an ordinary dangling key because the two need
        different responses: this is a one-newline fix in the upstream, while a
        genuinely missing crosswalk entry means the pin and the mapping have
        diverged.
        """
        return not self.resolved and bool(_SLUG_KEY.match(self.key))


@dataclass(frozen=True)
class Regime:
    """One crosswalk file — an external regulation and its citable entries."""

    name: str
    title: str
    description: str
    source_url: str
    entries: dict[str, dict[str, str]] = field(default_factory=dict)


# --------------------------------------------------------------- documents --
@dataclass(frozen=True)
class Doc:
    """Shared shape of a risk and a control."""

    id: str
    slug: str
    sequence: int
    type: str
    title: str
    doc_status: str
    summary: str
    path: str
    #: The catalogue this came from. Carried on the document so a multi-catalogue
    #: report can say which framework it is quoting, and so attribution can be
    #: collected from whatever was actually used.
    source: CatalogueSource | None = None
    related: tuple[str, ...] = ()
    references: tuple[Reference, ...] = ()

    @property
    def dangling(self) -> tuple[Reference, ...]:
        return tuple(r for r in self.references if not r.resolved)

    def refs_for(self, framework: str) -> tuple[Reference, ...]:
        return tuple(r for r in self.references if r.framework == framework)

    @property
    def frameworks(self) -> tuple[str, ...]:
        seen: list[str] = []
        for r in self.references:
            if r.framework not in seen:
                seen.append(r.framework)
        return tuple(seen)

    @property
    def catalogue(self) -> str:
        return self.source.name if self.source else ""


@dataclass(frozen=True)
class Risk(Doc):
    """One thing that can go wrong."""

    @property
    def type_label(self) -> str:
        return self.source.label_risk(self.type) if self.source else self.type


@dataclass(frozen=True)
class Control(Doc):
    """One mitigation.

    `mitigates` holds resolved risk ids, not the corpus's own slugs — resolution
    happens at load so a dangling cross-reference is found once, here, rather
    than by every caller that follows the link.
    """

    mitigates: tuple[str, ...] = ()

    @property
    def type_label(self) -> str:
        return self.source.label_control(self.type) if self.source else self.type


# --------------------------------------------------------------- catalogue --
@dataclass(frozen=True)
class Catalogue:
    """Every enabled catalogue's documents, merged.

    Merged rather than kept per-source because the consumers — a policy's
    `controls:` list, an `air.yaml` baseline — speak in control ids and should not
    have to know which framework a given id came from. Prefix uniqueness (enforced
    in `pf.air.sources.discover`) is what makes the merge unambiguous.
    """

    risks: dict[str, Risk]
    controls: dict[str, Control]
    regimes: dict[str, Regime]
    sources: tuple[CatalogueSource, ...] = ()
    commits: dict[str, str] = field(default_factory=dict)

    def get(self, doc_id: str) -> Risk | Control | None:
        key = doc_id.strip().upper()
        return self.risks.get(key) or self.controls.get(key)

    def controls_for(self, risk_id: str) -> tuple[Control, ...]:
        return tuple(c for c in self.sorted_controls if risk_id in c.mitigates)

    def risks_of_type(self, t: str) -> tuple[Risk, ...]:
        return tuple(r for r in self.sorted_risks if r.type == t.upper())

    def controls_of_type(self, t: str) -> tuple[Control, ...]:
        return tuple(c for c in self.sorted_controls if c.type == t.upper())

    def from_source(self, name: str) -> tuple[Doc, ...]:
        return tuple(d for d in (*self.sorted_risks, *self.sorted_controls)
                     if d.catalogue == name)

    @property
    def commit(self) -> str:
        """The single pinned commit, when exactly one catalogue is enabled.

        Ambiguous with several, so callers that want per-source detail read
        `commits`. Kept because the common case is one catalogue and every report
        wants to say which version it read.
        """
        return next(iter(self.commits.values()), "") if len(self.commits) == 1 else ""

    @cached_property
    def sorted_risks(self) -> tuple[Risk, ...]:
        return tuple(sorted(self.risks.values(), key=lambda d: (d.catalogue, d.sequence)))

    @cached_property
    def sorted_controls(self) -> tuple[Control, ...]:
        return tuple(sorted(self.controls.values(), key=lambda d: (d.catalogue, d.sequence)))

    @cached_property
    def dangling(self) -> tuple[tuple[str, Reference], ...]:
        """Every reference that did not resolve, with the document that made it."""
        out: list[tuple[str, Reference]] = []
        for d in (*self.sorted_risks, *self.sorted_controls):
            out.extend((d.id, r) for r in d.dangling)
        return tuple(out)

    @cached_property
    def unmitigated(self) -> tuple[str, ...]:
        """Risks no control claims. The catalogue's editorial state, reported."""
        claimed = {r for c in self.controls.values() for r in c.mitigates}
        return tuple(r for r in sorted(self.risks) if r not in claimed)

    @cached_property
    def attributions(self) -> tuple[str, ...]:
        """Credit lines every derived artefact must carry, deduplicated.

        Collected from the sources that are actually enabled rather than
        hardcoded into a template, so a catalogue swapped out takes its
        obligation with it and one added brings its own.
        """
        seen: list[str] = []
        for s in self.sources:
            if s.attribution and s.attribution not in seen:
                seen.append(s.attribution)
        return tuple(seen)


# ------------------------------------------------------------------- load --
def available(root: Path | str, sources: list[CatalogueSource] | None = None) -> bool:
    """True when at least one registered catalogue has a corpus on disk."""
    return bool(sources if sources is not None else available_sources(root))


def absent_reason(root: Path | str) -> str:
    """The evidence string every caller uses when nothing is available."""
    from pf.air.sources import all_sources

    paths = sorted({s.path for s in all_sources().values()})
    if not paths:
        return "no control catalogue is registered — see `pf air catalogues`"
    hint = " ".join(paths)
    return (
        f"no control catalogue checked out ({', '.join(paths)}) — run "
        f"`git submodule update --init {hint}`"
    )


def _load_regimes(src: CatalogueSource, base: Path) -> dict[str, Regime]:
    out: dict[str, Regime] = {}
    refs = base / src.layout.references
    if not refs.is_dir():
        return out
    for p in sorted(refs.glob(src.layout.references_glob)):
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        entries = data.get("entries") or {}
        out[p.stem] = Regime(
            name=p.stem,
            title=str(data.get("title", p.stem)),
            description=str(data.get("description", "")),
            source_url=str(data.get("source_url", "")),
            entries={str(k): (v or {}) for k, v in entries.items()},
        )
    return out


def _references(
    src: CatalogueSource, meta: dict[str, Any], regimes: dict[str, Regime]
) -> tuple[Reference, ...]:
    suffix = src.frontmatter.reference_suffix
    out: list[Reference] = []
    for key, value in meta.items():
        if not key.endswith(suffix) or not isinstance(value, list):
            continue
        framework = key[: -len(suffix)]
        regime = regimes.get(framework)
        for raw in value:
            ref_key = str(raw).strip()
            entry = regime.entries.get(ref_key) if regime else None
            if entry is None:
                # Kept rather than dropped. A citation we cannot resolve is the
                # finding `pf air verify` exists to surface; discarding it would
                # make a broken pin look like a clean one.
                out.append(Reference(framework, ref_key, ref_key, "", resolved=False))
            else:
                out.append(Reference(
                    framework, ref_key,
                    str(entry.get("title", ref_key)),
                    str(entry.get("url", regime.source_url if regime else "")),
                ))
    return tuple(out)


def _read_docs(src: CatalogueSource, d: Path) -> list[tuple[Path, dict[str, Any], str]]:
    fm = src.frontmatter
    out = []
    if not d.is_dir():
        return out
    for p in sorted(d.glob(src.layout.documents)):
        meta, body = split_frontmatter(p.read_text(encoding="utf-8"))
        if fm.sequence in meta and fm.type in meta:
            out.append((p, meta, body))
    return out


def load_source(root: Path | str, src: CatalogueSource) -> Catalogue:
    """One catalogue. `load()` is what callers normally want."""
    root = Path(root)
    base = src.root(root)
    if not src.available(root):
        raise NotVendored(f"{src.name}: {src.path} is not checked out")

    fm = src.frontmatter
    regimes = _load_regimes(src, base)

    def _common(p: Path, meta: dict[str, Any], body: str) -> dict[str, Any]:
        slug = p.name.split(fm.slug_separator, 1)[0]
        return {
            "slug": slug,
            "sequence": int(meta[fm.sequence]),
            "type": str(meta[fm.type]).upper(),
            "title": str(meta.get(fm.title, slug)),
            "doc_status": str(meta.get(fm.status, "")),
            "summary": _first_section(body),
            "path": str(p.relative_to(root)),
            "source": src,
            "references": _references(src, meta, regimes),
        }

    risks: dict[str, Risk] = {}
    risk_by_slug: dict[str, str] = {}
    for p, meta, body in _read_docs(src, base / src.layout.risks):
        c = _common(p, meta, body)
        rid = src.id_for(c["type"], c["sequence"])
        risk_by_slug[c["slug"]] = rid
        risks[rid] = Risk(
            id=rid, **c,
            related=tuple(str(x) for x in (meta.get(fm.related_risks) or [])),
        )

    controls: dict[str, Control] = {}
    for p, meta, body in _read_docs(src, base / src.layout.controls):
        c = _common(p, meta, body)
        cid = src.id_for(c["type"], c["sequence"])
        controls[cid] = Control(
            id=cid, **c,
            related=tuple(str(x) for x in (meta.get(fm.related_controls) or [])),
            # An unresolvable slug is kept verbatim so `verify` can name it;
            # dropping it would hide the break.
            mitigates=tuple(risk_by_slug.get(str(x), str(x))
                            for x in (meta.get(fm.mitigates) or [])),
        )

    return Catalogue(risks=risks, controls=controls, regimes=regimes,
                     sources=(src,), commits={src.name: _commit(base)})


def load(root: Path | str, sources: list[CatalogueSource] | None = None) -> Catalogue:
    """Every available catalogue, merged. Raises `NotVendored` when there are none."""
    root = Path(root)
    srcs = sources if sources is not None else available_sources(root)
    if not srcs:
        raise NotVendored(absent_reason(root))

    risks: dict[str, Risk] = {}
    controls: dict[str, Control] = {}
    regimes: dict[str, Regime] = {}
    commits: dict[str, str] = {}
    for src in srcs:
        one = load_source(root, src)
        risks.update(one.risks)
        controls.update(one.controls)
        # Crosswalks are keyed by regime stem. Two catalogues citing `eu-ai-act`
        # is the expected case, not a conflict: the first one loaded provides the
        # entry titles and the second's identical keys resolve against them.
        for name, regime in one.regimes.items():
            if name in regimes:
                merged = dict(regimes[name].entries)
                merged.update(regime.entries)
                regimes[name] = Regime(name, regimes[name].title, regimes[name].description,
                                       regimes[name].source_url, merged)
            else:
                regimes[name] = regime
        commits.update(one.commits)

    return Catalogue(risks=risks, controls=controls, regimes=regimes,
                     sources=tuple(srcs), commits=commits)


def catalogue_of(doc_id: str) -> CatalogueSource | None:
    """Which registered catalogue an id belongs to, without loading a corpus."""
    return source_for(doc_id)


def _commit(base: Path) -> str:
    """The pinned commit, read from the corpus's gitlink.

    Read from `.git` rather than by shelling out, because this can run inside the
    PreToolUse path and a subprocess per call is a cost with no matching benefit.
    """
    g = base / ".git"
    try:
        if g.is_file():
            gitdir = g.read_text(encoding="utf-8").split(":", 1)[1].strip()
            headfile = (base / gitdir / "HEAD").resolve()
        else:
            headfile = g / "HEAD"
        head = headfile.read_text(encoding="utf-8").strip()
        if head.startswith("ref:"):
            ref = head.split(":", 1)[1].strip()
            head = (headfile.parent / ref).read_text(encoding="utf-8").strip()
        return head[:40]
    except Exception:  # noqa: BLE001 — an unreadable gitlink is not worth failing on
        return ""
