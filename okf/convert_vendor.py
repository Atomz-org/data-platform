#!/usr/bin/env python3
"""Convert platform/src/pf/vendor/registry.yaml (24 real upstream entries)
into an OKF v0.2 bundle (okf/bundles/vendor/).

Real content: `why:` prose, `adopted:`/`declined:` paths and reasoning are
copied verbatim into the body. The registry's `adopted:` list is also mapped
onto OKF's actual provenance field — `sources[]` — one source per upstream
file we borrowed from, which is the one place OKF's schema and this
platform's own model describe almost the same thing.
"""

import pathlib

import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent
REG = REPO / "platform" / "src" / "pf" / "vendor" / "registry.yaml"
OUT = REPO / "okf" / "bundles" / "vendor" / "upstreams"
OUT.mkdir(parents=True, exist_ok=True)

reg = yaml.safe_load(REG.read_text())
upstreams = reg["upstreams"]


def body_for(u: dict) -> str:
    lines = [f"# {u.get('name', u['id'])}", "", u.get("why", "").strip(), ""]
    lines += ["## Adopted", ""]
    for a in u.get("adopted") or []:
        ours = a.get("ours")
        ours_s = ", ".join(ours) if isinstance(ours, list) else ours
        lines.append(f"- **{a.get('upstream')}** ({a.get('kind')}) -> {ours_s}")
        if a.get("note"):
            lines.append(f"  {a['note'].strip()}")
    lines += ["", "## Declined", ""]
    for d in u.get("declined") or []:
        lines.append(f"- **{d.get('what')}**")
        if d.get("why"):
            lines.append(f"  {d['why'].strip()}")
    return "\n".join(lines) + "\n"


rows = []
for u in upstreams:
    sources = []
    for a in u.get("adopted") or []:
        sources.append(
            {
                "id": f"{u['id']}:{a.get('upstream')}",
                "resource": u.get("url", ""),
                "title": a.get("upstream", ""),
            }
        )
    fm = {
        "type": "Vendor Upstream",
        "title": u.get("name", u["id"]),
        "description": u.get("summary", ""),
        "resource": u.get("url", ""),
        "tags": ["vendor", u.get("role", "unknown"), u.get("licence", "unknown").replace(" ", "-")],
        "status": "stable",
        "sources": sources,
    }
    fm_yaml = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, default_flow_style=False)
    out_path = OUT / f"{u['id'].replace('/', '-')}.md"
    out_path.write_text(f"---\n{fm_yaml}---\n\n{body_for(u)}", encoding="utf-8")
    rows.append((u["id"], len(sources), out_path.relative_to(REPO)))

for uid, n_sources, path in rows:
    print(f"{uid:32s} {n_sources:2d} source(s) -> {path}")
print(f"\n{len(rows)} concepts written")
