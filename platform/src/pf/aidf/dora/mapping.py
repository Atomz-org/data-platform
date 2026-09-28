"""The statutory matrix: which DORA article each automated check evidences.

Read from `data/mappings.json`, which is the single place an article, its
requirement and its checks are stated. The audit renders this file's rows; the
docs are generated from it; a test asserts every check kind it names is one the
audit knows how to evaluate — so a new row cannot claim evidence nobody
produces.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MAPPINGS_FILE = Path(__file__).parents[1] / "data" / "mappings.json"

CHECK_KINDS: tuple[str, ...] = (
    "prowler", "trivy", "provenance", "file", "declaration", "workflow", "air", "live_github",
)


@dataclass(frozen=True)
class Check:
    id: str
    kind: str
    description: str
    #: kind-specific fields, kept as written.
    spec: dict[str, Any] = field(default_factory=dict)

    def prefixes_for(self, provider: str) -> list[str]:
        p = self.spec.get("prefixes") or {}
        return list(p.get(provider, [])) if isinstance(p, dict) else []

    @property
    def compliance_keys(self) -> list[str]:
        return [str(k).lower() for k in self.spec.get("compliance_keys", [])]

    @property
    def requirements(self) -> list[str]:
        """Requirement ids in the scanner's own framework (`DORA-Art9`)."""
        return [str(r) for r in self.spec.get("requirements", [])]


@dataclass(frozen=True)
class Article:
    id: str
    title: str
    requirement: str
    checks: tuple[Check, ...]

    @property
    def label(self) -> str:
        return self.id if self.id.startswith("RTS") else f"Art. {self.id}"


@dataclass(frozen=True)
class Mapping:
    version: int
    regulation: str
    articles: tuple[Article, ...]
    kinds: dict[str, str]

    def article(self, article_id: str) -> Article | None:
        return next((a for a in self.articles if a.id == str(article_id)), None)

    def checks(self) -> list[Check]:
        return [c for a in self.articles for c in a.checks]


def load_mapping(path: Path | None = None) -> Mapping:
    doc = json.loads((path or MAPPINGS_FILE).read_text(encoding="utf-8"))
    articles: list[Article] = []
    for a in doc.get("articles", []):
        checks = tuple(
            Check(id=str(c["id"]), kind=str(c["kind"]), description=str(c.get("description", "")),
                  spec={k: v for k, v in c.items() if k not in ("id", "kind", "description")})
            for c in a.get("checks", [])
        )
        articles.append(Article(id=str(a["id"]), title=str(a["title"]), requirement=str(a.get("requirement", "")),
                                checks=checks))
    return Mapping(version=int(doc.get("version", 1)), regulation=str(doc.get("regulation", "")),
                   articles=tuple(articles), kinds=dict(doc.get("check_kinds", {})))


def validate_mapping(m: Mapping) -> list[str]:
    """Problems with the matrix itself. Empty is good."""
    problems: list[str] = []
    seen: set[str] = set()
    for a in m.articles:
        if not a.checks:
            problems.append(f"article {a.id} has no checks")
        for c in a.checks:
            if c.id in seen:
                problems.append(f"check id {c.id} appears twice")
            seen.add(c.id)
            if c.kind not in CHECK_KINDS:
                problems.append(f"check {c.id}: unknown kind {c.kind!r}")
            if c.kind == "file" and not c.spec.get("path"):
                problems.append(f"check {c.id}: kind file needs a path")
            if c.kind == "workflow" and not c.spec.get("file"):
                problems.append(f"check {c.id}: kind workflow needs a file")
            if c.kind == "declaration" and not c.spec.get("key"):
                problems.append(f"check {c.id}: kind declaration needs a key")
            if c.kind == "prowler" and not (c.spec.get("prefixes") or c.spec.get("compliance_keys")):
                problems.append(f"check {c.id}: kind prowler needs prefixes or compliance_keys")
    return problems
