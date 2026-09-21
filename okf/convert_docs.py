#!/usr/bin/env python3
"""Convert docs/*.md into an OKF v0.2 bundle (okf/bundles/docs/).

Real content, real conversion — the body is copied verbatim (frontmatter
prepended only), so `okf validate`/`lint`/`graph` findings below reflect the
actual prose corpus, not a cleaned-up sample. Cross-doc links are rewritten
from `docs/X.md` / `[text](X.md)` to the bundle-relative form OKF expects
(`/reference/x.md`); anything that doesn't match that pattern is left alone,
and whatever `okf validate` then reports as broken is the honest answer to
"how much of this would need fixing by hand."
"""

import pathlib
import re

import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
OUT = REPO / "okf" / "bundles" / "docs" / "reference"
OUT.mkdir(parents=True, exist_ok=True)

# type + one-line description, taken from each file's own opening sentence
# (not invented) + tags reflecting the platform's own vocabulary for it.
META = {
    "AI-GOVERNANCE-ARCHITECTURE.md": ("Reference", ["governance", "ai-risk", "architecture"]),
    "AIR.md": ("Reference", ["governance", "ai-risk", "controls"]),
    "ARCHITECTURE-MAPS.md": ("Reference", ["architecture", "kg", "generated-docs"]),
    "ARCHITECTURE.md": ("Reference", ["architecture", "generated-docs"]),
    "ARTIFACTS.md": ("Reference", ["artifacts", "storage"]),
    "CLAUDE-CODE.md": ("Playbook", ["session-layer", "power-tools", "runbook"]),
    "ENGINEERING.md": ("Reference", ["dlt", "dbt", "layer-contract"]),
    "GOVERNANCE.md": ("Reference", ["governance", "provenance"]),
    "KG-ATLAS.md": ("Reference", ["kg", "graph"]),
    "POLICY.md": ("Reference", ["governance", "policy"]),
    "PROJECT-ATLAS.md": ("Reference", ["kg", "atlas"]),
    "SCAFFOLDING.md": ("Playbook", ["scaffolding", "runbook"]),
    "SEMANTICS.md": ("Reference", ["semantics", "metrics"]),
    "STACK.md": ("Reference", ["control-plane", "stack"]),
    "VENDOR-CARD.md": ("Reference", ["vendor", "generated-docs"]),
    "VENDOR.md": ("Reference", ["vendor", "generated-docs"]),
}

# Three real link shapes found in docs/*.md, by grepping the corpus rather
# than guessing: `docs/X.md` (from README, which sits one level up), a bare
# sibling `X.md` (docs linking each other from the same directory), and a
# `../platform/...` or `../vendor/...` path into actual source — which OKF has
# no way to express as anything but a broken concept link, and is left alone
# on purpose so `okf validate` reports it. That third category is the finding.
DOC_NAMES = "|".join(re.escape(p.stem) for p in DOCS.glob("*.md"))
LINK_RE = re.compile(rf"\]\((?:docs/)?({DOC_NAMES})\.md(#[^)]*)?\)")


def slug(name: str) -> str:
    return name.lower().replace(".md", "")


def rewrite_links(body: str) -> str:
    return LINK_RE.sub(lambda m: f"](/reference/{slug(m.group(1))}.md{m.group(2) or ''})", body)


rows = []
for src in sorted(DOCS.glob("*.md")):
    name = src.name
    if name not in META:
        continue
    typ, tags = META[name]
    text = src.read_text(encoding="utf-8")
    body = rewrite_links(text)
    first_para = next((ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")), "")
    description = first_para[:180].rstrip()
    fm = {
        "type": typ,
        "title": name.replace(".md", "").replace("-", " ").title(),
        "description": description,
        "tags": tags,
        "status": "stable",
        "generated": {"by": "process:claude-code/okf-experiment", "at": "2026-09-21T00:00:00Z"},
    }
    out_path = OUT / f"{slug(name)}.md"
    fm_yaml = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, default_flow_style=False)
    out_path.write_text(f"---\n{fm_yaml}---\n\n{body}", encoding="utf-8")
    rows.append((name, out_path.relative_to(REPO), len(text)))

for name, out, size in rows:
    print(f"{name:38s} -> {out}  ({size} bytes)")
print(f"\n{len(rows)} concepts written")
