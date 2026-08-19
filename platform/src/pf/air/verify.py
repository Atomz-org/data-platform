"""The contract between us and the vendored corpus.

`registry.yaml` pins `docs/_mitigations`, `docs/_risks` and
`docs/_data/references` as `kind: data`, whose severity is `error`. That is a
claim, and this module is what makes it true: a pin bump that renames a control,
retires a risk still cited by a control, or changes a `type:` letter fails here
rather than showing up months later as a baseline that silently stopped matching
anything.

## What is checked, and what deliberately is not

Checked: the corpus parses, both collections are non-empty, ids are unique, every
`mitigates:` resolves to a real risk, every `*_references:` key resolves in its
crosswalk file, and every crosswalk file a document cites actually exists.

Not checked: `doc-status`. Upstream's status ladder (Pre-Draft ... Approved-
Specification) records *their* working group's consensus, and letting it decide
whether our build passes would hand that group a vote on our merge gate. It is
parsed and displayed; it gates nothing. The registry entry records this decline.

Not checked either: that risks have controls. `Catalogue.unmitigated` reports the
gap because it is worth seeing, but an unmitigated risk is upstream's editorial
state, not a defect in our pin.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pf.air.catalogue import Catalogue, NotVendored, absent_reason, available, load


@dataclass(frozen=True)
class Finding:
    level: str  # "fail" | "warn" | "ok"
    code: str
    detail: str


@dataclass
class VerifyReport:
    findings: list[Finding]
    risks: int = 0
    controls: int = 0
    regimes: int = 0
    references: int = 0
    commit: str = ""
    vendored: bool = True

    @property
    def failures(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "fail"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "warn"]

    @property
    def ok(self) -> bool:
        return not self.failures

    @property
    def exit_code(self) -> int:
        return 1 if self.failures else 0


def verify(root: Path | str) -> VerifyReport:
    """Check the corpus against its own frontmatter contract.

    An absent submodule is *not* a failure — it is `vendored=False` and exit 0,
    so a shallow clone that never ran `git submodule update` is not punished for
    it. The failure mode this guards is a corpus that is present and wrong.
    """
    root = Path(root)
    if not available(root):
        return VerifyReport(
            findings=[Finding("warn", "corpus.absent", absent_reason(root))],
            vendored=False,
        )

    try:
        cat = load(root)
    except NotVendored as exc:  # pragma: no cover — available() just said otherwise
        return VerifyReport(
            findings=[Finding("warn", "corpus.absent", str(exc))], vendored=False
        )
    except Exception as exc:  # noqa: BLE001 — a corpus we cannot parse is the finding
        return VerifyReport(
            findings=[Finding("fail", "corpus.unparseable", f"{type(exc).__name__}: {exc}")]
        )

    out: list[Finding] = []
    _counts(cat, out)
    _types(cat, out)
    _cross_references(cat, out)
    _citations(cat, out)

    refs = sum(len(d.references) for d in (*cat.sorted_risks, *cat.sorted_controls))
    if not out:
        out.append(
            Finding(
                "ok",
                "corpus.intact",
                f"{len(cat.risks)} risks, {len(cat.controls)} controls, "
                f"{refs} citations across {len(cat.regimes)} regimes",
            )
        )
    return VerifyReport(
        findings=out,
        risks=len(cat.risks),
        controls=len(cat.controls),
        regimes=len(cat.regimes),
        references=refs,
        commit=cat.commit,
    )


def _counts(cat: Catalogue, out: list[Finding]) -> None:
    """A corpus on disk that parsed to nothing is a layout that has moved.

    Reported per source and against that source's own declared layout, so the
    message names the directory this catalogue actually expects rather than the
    one the first catalogue happened to use.
    """
    for src in cat.sources:
        docs = cat.from_source(src.name)
        if not any(d.id in cat.risks for d in docs):
            out.append(Finding("fail", "corpus.no_risks",
                               f"{src.name}: {src.path}/{src.layout.risks} parsed to nothing"))
        if not any(d.id in cat.controls for d in docs):
            out.append(Finding("fail", "corpus.no_controls",
                               f"{src.name}: {src.path}/{src.layout.controls} parsed to nothing"))
    if not cat.regimes:
        out.append(Finding(
            "fail", "corpus.no_regimes",
            "no crosswalk files parsed — every citation would dangle"))


def _types(cat: Catalogue, out: list[Finding]) -> None:
    """An unknown type code changes every derived id in that class.

    Checked against the vocabulary the document's *own* catalogue declares. A
    source that declares none accepts anything — the honest default for a
    catalogue whose vocabulary we were never told, and the reason this is not a
    module-level constant.
    """
    for kind, docs, vocab in (
        ("risk", cat.sorted_risks, lambda s: s.risk_types),
        ("control", cat.sorted_controls, lambda s: s.control_types),
    ):
        for d in docs:
            if d.source is None:
                continue
            known = vocab(d.source)
            if known and d.type not in known:
                out.append(Finding(
                    "fail", f"{kind}.unknown_type",
                    f"{d.path}: type '{d.type}' is not one of {', '.join(known)} "
                    f"— id {d.id} is derived from it"))


def _cross_references(cat: Catalogue, out: list[Finding]) -> None:
    """`mitigates:` must land on a risk that exists."""
    for c in cat.sorted_controls:
        for target in c.mitigates:
            if target not in cat.risks:
                out.append(
                    Finding(
                        "fail",
                        "control.dangling_mitigates",
                        f"{c.id} ({c.path}) mitigates '{target}', which is not a risk "
                        f"in this corpus",
                    )
                )


def _citations(cat: Catalogue, out: list[Finding]) -> None:
    """Every `<regime>_references:` key must resolve in `_data/references/<regime>.yml`.

    These keys are the crosswalk, and upstream's own README calls renaming one a
    breaking change. A dangling key means a citation that would print as a bare
    identifier with no title and no URL — a compliance report that cites nothing.
    """
    malformed: dict[str, list[str]] = {}
    for doc_id, ref in cat.dangling:
        if ref.malformed:
            # Upstream's own frontmatter, absorbed by a comment with no trailing
            # newline. A warning, not a failure: it is a one-newline fix in
            # someone else's repository, and failing our merge over it would make
            # our build hostage to their typo. Grouped so seven files read as one
            # defect rather than nineteen.
            malformed.setdefault(doc_id, []).append(f"{ref.framework}:{ref.key}")
        elif ref.framework not in cat.regimes:
            out.append(
                Finding(
                    "fail",
                    "citation.unknown_regime",
                    f"{doc_id} cites '{ref.framework}', but "
                    f"docs/_data/references/{ref.framework}.yml does not exist",
                )
            )
        else:
            out.append(
                Finding(
                    "fail",
                    "citation.dangling_key",
                    f"{doc_id} cites {ref.framework}:{ref.key}, which is not an entry "
                    f"in docs/_data/references/{ref.framework}.yml",
                )
            )

    if malformed:
        docs = ", ".join(sorted(malformed))
        out.append(
            Finding(
                "warn",
                "corpus.frontmatter_malformed",
                f"{len(malformed)} upstream document(s) have a list comment running "
                f"into the next key with no newline, so `related_risks:` was parsed as "
                f"part of the comment and its items absorbed as citations: {docs}. "
                f"Those documents have lost their related-risk links upstream. "
                f"Worth a one-newline pull request to finos/ai-governance-framework; "
                f"nothing on our side is wrong and nothing here is blocked.",
            )
        )
