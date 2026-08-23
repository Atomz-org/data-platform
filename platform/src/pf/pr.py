"""One report per pull request, from the project's point of view.

A diff tells a reviewer which lines moved. It does not tell them that
`stg_stripe__charges` feeds four marts and a metric that the finance exposure
owner depends on — and that is the only fact that decides whether the PR is safe.
This assembles what a reviewer would otherwise have to reconstruct by hand:

    per project touched   blast radius, conformance, readiness
    repo-wide             vendor drift, path-gate verdicts
    verdict               block / review / clear

WHY IT IS ALSO A FILE, NOT JUST A COMMENT. The report is written to
`data/pr/<n>.json` and read by `pf ui`. A PR comment is where a human reads it;
the JSON is where the control plane reads it, so the dashboard shows the same
verdict CI posted rather than a second opinion computed differently.

WHY THE VERDICT IS NEVER "APPROVED". `clear` means nothing downstream breaks and
no gate fired. It is a statement about blast radius, not about whether the change
is correct — that judgement stays with the reviewer, and blurring the two is how
a green check starts substituting for reading the diff.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import groupby
from pathlib import Path
from typing import Any

VERDICTS = ("block", "review", "clear")


def _git(root: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def changed_files(root: Path, base: str = "", exclude_deleted: bool = False) -> list[str]:
    """Files this PR touches.

    Falls back through three sources so the command is useful locally, on a
    branch and in CI: an explicit base ref, the merge-base with the default
    branch, then the working tree.

    `exclude_deleted` exists for the path gate. The gate asks "was this edited by
    hand", and a deleted file was not — without the filter, removing a generated
    artefact from tracking is reported as a gate violation for touching it.
    Blast radius still uses the full list, because deleting a model is exactly
    the kind of change the blast radius is for.
    """
    filt = ["--diff-filter=d"] if exclude_deleted else []

    def against(ref: str) -> list[str] | None:
        mb = _git(root, "merge-base", ref, "HEAD")
        if not mb:
            return None
        # Two-arg diff, not `mb..HEAD`: comparing the *working tree* to the merge
        # base picks up uncommitted work too. In CI they are the same thing; on a
        # branch mid-change they are not, and the report is most useful exactly
        # then.
        out = _git(root, "diff", "--name-only", *filt, mb)
        return [ln for ln in out.splitlines() if ln]

    if base:
        # An explicit base is an instruction, not a hint. Falling back to
        # origin/main when the diff came back empty silently answered a
        # different question than the one asked — and reported 747 files for a
        # one-file change.
        return against(base) or []

    for ref in ("origin/main", "origin/master", "main", "master"):
        found = against(ref)
        if found:
            return found
    out = _git(root, "status", "--porcelain")
    return [ln[3:].strip() for ln in out.splitlines()
            if ln[3:].strip() and not (exclude_deleted and ln[:2].strip() == "D")]


# ------------------------------------------------------------------ model ----
@dataclass
class ProjectSlice:
    group: str
    project: str
    files: list[str] = field(default_factory=list)
    nodes: list[str] = field(default_factory=list)
    severity: str = "safe"
    impacted: int = 0
    owners: list[str] = field(default_factory=list)
    impact: dict[str, Any] = field(default_factory=dict)
    conformance_errors: list[str] = field(default_factory=list)
    conformance_warnings: int = 0
    ready: bool = True
    missing: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "group": self.group, "project": self.project, "files": self.files,
            "nodes": self.nodes, "severity": self.severity, "impacted": self.impacted,
            "owners": self.owners, "impact": self.impact,
            "conformance_errors": self.conformance_errors,
            "conformance_warnings": self.conformance_warnings,
            "ready": self.ready, "missing": self.missing,
        }


@dataclass
class PRReport:
    number: int
    title: str
    branch: str
    base: str
    commit: str
    generated_at: str
    files: list[str] = field(default_factory=list)
    projects: list[ProjectSlice] = field(default_factory=list)
    gate_denied: list[str] = field(default_factory=list)
    vendor: list[dict[str, Any]] = field(default_factory=list)
    platform_touched: list[str] = field(default_factory=list)
    readiness_score: int = 0

    @property
    def verdict(self) -> str:
        if self.gate_denied or any(p.severity == "breaking" for p in self.projects) \
                or any(p.conformance_errors for p in self.projects):
            return "block"
        if any(p.severity == "review" for p in self.projects) \
                or self.platform_touched \
                or any(v.get("needs_review") for v in self.vendor):
            return "review"
        return "clear"

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number, "title": self.title, "branch": self.branch,
            "base": self.base, "commit": self.commit,
            "generated_at": self.generated_at, "verdict": self.verdict,
            "files": self.files, "projects": [p.to_dict() for p in self.projects],
            "gate_denied": self.gate_denied, "vendor": self.vendor,
            "platform_touched": self.platform_touched,
            "readiness_score": self.readiness_score,
        }


# ----------------------------------------------------------------- build ----
def build(root: str | Path, number: int = 0, base: str = "", title: str = "") -> PRReport:
    from pf.loops.audit import audit as loop_audit
    from pf.loops.audit import project_readiness
    from pf.loops.gate import check_path, nodes_for, project_for

    root = Path(root)
    files = [f for f in changed_files(root, base) if f]
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    commit = _git(root, "rev-parse", "HEAD")

    # Path gate first: a denied path is a stop, and computing blast radius for a
    # change that must not land at all is wasted work and a misleading report.
    # `check_path` per file, not `check_paths`: the latter also applies the
    # per-run `maxFiles` cap, which exists to keep one *agent run* small. A pull
    # request legitimately touches more files than an agent should in one go, and
    # conflating the two makes every real PR report BLOCK for the wrong reason.
    denied = [f"{g.path}: {g.message}"
              for g in (check_path(f, root)
                        for f in changed_files(root, base, exclude_deleted=True))
              if g.blocked]

    readiness = {(r.group, r.project): r for r in project_readiness(root)}

    buckets: dict[tuple[str, str, Path], list[str]] = {}
    platform_touched = []
    for f in files:
        if f.startswith("platform/"):
            platform_touched.append(f)
        hit = project_for(f, root)
        if hit:
            buckets.setdefault(hit, []).append(f)

    slices: list[ProjectSlice] = []
    for (g, p, d), fs in sorted(buckets.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        s = ProjectSlice(group=g, project=p, files=sorted(fs))
        s.nodes = sorted({n for f in fs for n in nodes_for(f)})
        _add_impact(d, s)
        _add_conformance(d, s)
        r = readiness.get((g, p))
        if r is not None:
            s.ready, s.missing = r.ready, r.missing
        slices.append(s)

    score, _ = loop_audit(root)

    return PRReport(
        number=number, title=title or _git(root, "log", "-1", "--format=%s"),
        branch=branch, base=base or _default_base(root), commit=commit,
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        files=files, projects=slices, gate_denied=denied,
        vendor=_vendor_slice(root), platform_touched=platform_touched,
        readiness_score=score,
    )


def _default_base(root: Path) -> str:
    for ref in ("origin/main", "origin/master", "main", "master"):
        if _git(root, "rev-parse", "--verify", "--quiet", ref):
            return ref
    return ""


def _add_impact(pdir: Path, s: ProjectSlice) -> None:
    gp = pdir / "kg" / "graph.duckdb"
    if not s.nodes or not gp.exists():
        return
    from pf.kg.impact import impact_of_many

    try:
        rep = impact_of_many(gp, s.nodes)
    except KeyError:
        # A brand-new model is not in the graph yet. That is not "safe" and not
        # "breaking" — it means the graph is stale, and saying so beats guessing.
        s.severity = "review"
        s.impact = {"note": "one or more nodes are not in the graph — run `pf kg build`"}
        return
    s.severity, s.impacted, s.owners = rep.severity, rep.total, rep.owners
    s.impact = rep.to_dict()


def _add_conformance(pdir: Path, s: ProjectSlice) -> None:
    from pf.ontology.validate import validate_project

    try:
        issues = validate_project(pdir)
    except Exception as exc:  # noqa: BLE001
        s.conformance_errors = [f"{type(exc).__name__}: {exc}"[:160]]
        return
    s.conformance_errors = [str(i) for i in issues if i.severity == "error"]
    s.conformance_warnings = sum(1 for i in issues if i.severity != "error")


def _vendor_slice(root: Path) -> list[dict[str, Any]]:
    try:
        from pf.vendor.model import drift
    except Exception:  # noqa: BLE001
        return []
    out = []
    for d in drift(root):
        if not d.moved and d.locked:
            continue
        out.append({
            "id": d.upstream_id, "name": d.name,
            "locked": d.locked[:8], "current": d.current[:8],
            "commits_behind": d.commits_behind,
            "needs_review": d.needs_review, "severity": d.severity,
            "paths": [{"path": p.path, "kind": p.kind, "state": p.state,
                       "severity": p.severity, "ours": p.ours} for p in d.paths],
        })
    return out


# ---------------------------------------------------------------- mermaid ----
# The same report as an architecture chart, rendered by GitHub inside the comment.
#
# WHY IT EXISTS ALONGSIDE THE TABLE. The table answers "how bad", one project per
# row. It cannot show the *shape* — that a platform edit lands in three sisters at
# once, or that one staging model is what reaches the finance exposure. A reviewer
# reconstructs that shape in their head from the rows; drawing it is cheaper and
# does not vary with how carefully they read.
#
# WHY THE COLOURS ARE HARD-CODED PALE FILLS. GitHub renders one mermaid source on
# both a light and a dark page and does not recolour an explicit `classDef` fill.
# A saturated fill that reads on white is unreadable on black, so every node is a
# pale fill + a saturated stroke of the same hue + near-black ink: the fill is
# theme-invariant, so one palette stays legible in both (worst measured 14.4:1).
#
# Hue carries the *layer* — blue change, violet platform, yellow touched node,
# aqua model, magenta metric, orange exposure. The four reserved status hues carry
# severity and never a layer, so a red node always means danger and never "the
# fourth thing". Both are spelled out in the label too; the chart never leans on
# colour alone, which is also what makes it survive a colourblind reviewer and a
# greyscale print.
MM_MAX_PROJECTS = 6

# fill / stroke, keyed by the job the node does.
#
# The container fills at the bottom are deliberately weaker than the node fills.
# They are styled at all because mermaid's *default* subgraph fill is a yellow
# that reads as "warning" — a neutral group box has to be asked for, or every
# group on every PR looks like it is flagging something. Severity keeps a tint
# here (it is the box's whole point) but a pale one, so the layer-coloured nodes
# sitting inside still separate from their background.
MM_CLASSDEF = (
    ("pr", "#cde2fb", "#2a78d6"),
    ("platform", "#ded9f7", "#4a3aa7"),
    ("project", "#e3eefc", "#2a78d6"),
    ("node", "#fbe8bd", "#eda100"),
    ("model", "#d6f2e6", "#1baf7a"),
    ("metric", "#fadfe8", "#e87ba4"),
    ("exposure", "#fbdccf", "#eb6834"),
    ("vendor", "#e8e7e2", "#898781"),
    ("good", "#d5f2d5", "#0ca30c"),
    ("warning", "#fdeccb", "#fab219"),
    ("critical", "#f6d8d8", "#d03b3b"),
    ("grp", "#f6f6f4", "#898781"),
    ("sevBreaking", "#fdefef", "#d03b3b"),
    ("sevReview", "#fef7e8", "#fab219"),
    ("sevSafe", "#eef9ee", "#0ca30c"),
)

MM_VERDICT = {"block": ("critical", "BLOCK"), "review": ("warning", "REVIEW"),
              "clear": ("good", "CLEAR")}
MM_SEV = {"breaking": ("sevBreaking", "breaking"), "review": ("sevReview", "review"),
          "safe": ("sevSafe", "safe")}


def _mm(text: Any, limit: int = 46) -> str:
    """Make `text` safe to sit inside a double-quoted mermaid label.

    `#` opens a mermaid entity reference and `"` ends the label early — an
    unescaped one in a dbt node name or a branch name turns the whole diagram
    into a parse error, which on GitHub renders as a red box where the
    architecture should be. `<` matters for a subtler reason: GitHub renders
    mermaid with `htmlLabels` on, so an exposure owner written
    `Data Science <ds@jaffle.test>` has its address parsed as a tag and silently
    swallowed — the label loses the very name the reviewer needs to notify.

    Callers pass *fragments*; the deliberate `<br/>` separators are concatenated
    outside, so escaping here never eats a line break. Order matters: `#` goes
    first, so the `#` this introduces for the others is not escaped twice.
    """
    t = " ".join(str(text).split())
    if len(t) > limit:
        t = t[: limit - 1] + "…"
    for a, b in (("#", "#35;"), ('"', "#quot;"), ("<", "#lt;"), (">", "#gt;")):
        t = t.replace(a, b)
    return t


def _mm_project(out: list[str], n: int, p: ProjectSlice) -> None:
    """One project as a left-to-right chain: what changed → what it reaches."""
    cls, word = MM_SEV.get(p.severity, ("good", p.severity))
    out.append(f'        subgraph P{n}["{_mm(p.project)} · {word}"]')
    out.append("            direction LR")

    chain = [f"P{n}F"]
    out.append(f'            P{n}F["{len(p.files)} file(s) changed"]:::project')

    if p.nodes:
        # Leaf name only: ids arrive as `model:stg_stripe__charges`, and the kind
        # prefix repeats on every node in a box already labelled "dbt node(s)".
        sample = ", ".join(x.rsplit(":", 1)[-1].rsplit(".", 1)[-1] for x in p.nodes[:2])
        if len(p.nodes) > 2:
            sample += f" +{len(p.nodes) - 2}"
        chain.append(f"P{n}N")
        out.append(f'            P{n}N["{len(p.nodes)} dbt node(s)<br/>'
                   f'{_mm(sample, 40)}"]:::node')

    for key, sfx, cls_, label in (("models", "MD", "model", "models"),
                                  ("metrics", "MT", "metric", "metrics"),
                                  ("exposures", "EX", "exposure", "exposures")):
        items = p.impact.get(key) or []
        if not items:
            continue
        extra = ""
        # The owners hang off the exposure box because that is the one layer a
        # reviewer has to *act* on before merging — a name in the picture beats
        # a name in a table nobody scrolled to.
        if key == "exposures" and p.owners:
            extra = "<br/>" + _mm(", ".join(p.owners[:2]), 34)
        chain.append(f"P{n}{sfx}")
        out.append(f'            P{n}{sfx}["{label} · {len(items)}{extra}"]:::{cls_}')

    out.append("            " + " --> ".join(chain))

    # A stale graph is neither safe nor breaking, and the chart has to say which
    # of the two it is failing to tell you.
    if p.impact.get("note"):
        out.append(f'            P{n}Q["graph stale<br/>run pf kg build"]:::warning')
        out.append(f"            P{n}F --> P{n}Q")
    if p.conformance_errors:
        out.append(f'            P{n}C["{len(p.conformance_errors)} conformance '
                   f'error(s)"]:::critical')
        out.append(f"            P{n}F --> P{n}C")

    out.append("        end")
    out.append(f"        class P{n} {cls}")


def mermaid(r: PRReport) -> str:
    """The report as a fenced mermaid block, ready to paste into the comment."""
    v_cls, v_word = MM_VERDICT[r.verdict]
    head = f"PR {r.number}" if r.number else r.branch
    out = ["```mermaid", "flowchart LR",
           (f'    PR(["{_mm(head, 30)}<br/>{len(r.files)} file(s) · '
           f'{v_word}"]):::{v_cls}')]

    if r.gate_denied:
        out.append(f'    GATE["path gate denied<br/>{len(r.gate_denied)} path(s)'
                   f'"]:::critical')
        out.append("    PR --> GATE")

    if r.platform_touched:
        out.append(f'    PLAT["platform/ · {len(r.platform_touched)} file(s)<br/>'
                   f'shared by every project"]:::platform')
        out.append("    PR --> PLAT")

    shown = r.projects[:MM_MAX_PROJECTS]
    numbered = sorted(enumerate(shown), key=lambda np: np[1].group)
    for gi, (gname, members) in enumerate(groupby(numbered, key=lambda np: np[1].group)):
        out.append(f'    subgraph G{gi}["{_mm(gname)}"]')
        out.append("        direction LR")
        for n, p in members:
            _mm_project(out, n, p)
        out.append("    end")
        out.append(f"    class G{gi} grp")

    for n, _ in numbered:
        out.append(f"    PR --> P{n}F")
    if r.platform_touched:
        # Dotted, and labelled once: the platform edit is not *in* these projects,
        # it arrives in them.
        for i, (n, _) in enumerate(numbered):
            arrow = "-.->|lands in|" if i == 0 else "-.->"
            out.append(f"    PLAT {arrow} P{n}F")

    if not r.projects:
        out.append('    NONE["no project files touched"]:::vendor')
        out.append("    PR --> NONE")
    elif len(r.projects) > MM_MAX_PROJECTS:
        rest = len(r.projects) - MM_MAX_PROJECTS
        out.append(f'    MORE["+{rest} more project(s)<br/>see the table below"]:::vendor')
        out.append("    PR --> MORE")

    if r.vendor:
        need = sum(1 for x in r.vendor if x.get("needs_review"))
        out.append(f'    VEN["vendor · {len(r.vendor)} upstream(s) moved<br/>'
                   f'{need} need review"]:::{"warning" if need else "vendor"}')
        out.append("    PR --> VEN")

    for name, fill, stroke in MM_CLASSDEF:
        out.append(f"    classDef {name} fill:{fill},stroke:{stroke},"
                   f"stroke-width:2px,color:#0b0b0b")
    out.append("```")
    return "\n".join(out)


# --------------------------------------------------------------- markdown ----
BADGE = {"block": "🔴 **BLOCK**", "review": "🟡 **REVIEW**", "clear": "🟢 **CLEAR**"}
SEV = {"breaking": "🔴 breaking", "review": "🟡 review", "safe": "🟢 safe"}

MARKER = "<!-- pf-pr-report -->"


def markdown(r: PRReport) -> str:
    """The PR comment. Verdict first, because that is what gets read."""
    out = [MARKER, f"## {BADGE[r.verdict]} — platform impact report", ""]

    if r.verdict == "clear":
        out.append("Nothing downstream breaks, no gate fired, every touched "
                   "project conforms.")
    elif r.verdict == "block":
        out.append("This change breaks something downstream or violates the path "
                   "gate. Details below.")
    else:
        out.append("Landable, but a human should look at the items below before "
                   "merging.")
    out.append("")

    # Above the tables, not inside a <details>: a collapsed diagram is a diagram
    # nobody looks at, and orientation is only useful before the detail.
    out += [mermaid(r), ""]

    if r.gate_denied:
        out += ["### 🚫 Path gate", ""]
        out += [f"- `{d}`" for d in r.gate_denied]
        out.append("")

    if r.projects:
        out += ["### Projects touched", "",
                "| project | files | blast radius | exposure owners | conformance | ready |",
                "|---|---:|---|---|---|---|"]
        for p in r.projects:
            owners = ", ".join(p.owners) if p.owners else "—"
            conf = ("✅" if not p.conformance_errors
                    else f"❌ {len(p.conformance_errors)} error(s)")
            if p.conformance_warnings:
                conf += f" ({p.conformance_warnings} warn)"
            ready = "✅" if p.ready else "⚠️ " + ", ".join(p.missing)
            out.append(f"| `{p.group}/{p.project}` | {len(p.files)} | "
                       f"{SEV.get(p.severity, p.severity)} · {p.impacted} node(s) | "
                       f"{owners} | {conf} | {ready} |")
        out.append("")
        for p in r.projects:
            if p.impact.get("models") or p.impact.get("metrics") or p.impact.get("exposures"):
                out += [(f"<details><summary>Blast radius — "
                        f"<code>{p.group}/{p.project}</code></summary>"), ""]
                for key, label in (("models", "Models"), ("metrics", "Metrics"),
                                   ("exposures", "Exposures"), ("dimensions", "Dimensions")):
                    items = p.impact.get(key) or []
                    if items:
                        out.append(f"**{label}** ({len(items)}): "
                                   + ", ".join(f"`{i['name']}`" for i in items[:20]))
                for e in p.conformance_errors[:10]:
                    out.append(f"- ❌ {e}")
                out += ["", "</details>", ""]
    else:
        out += ["_No project files touched._", ""]

    if r.platform_touched:
        out += ["### ⚠️ Shared platform touched", "",
                ("These files are shared by every project — a change here lands in "
                "all of them at once."), ""]
        out += [f"- `{f}`" for f in r.platform_touched[:20]]
        if len(r.platform_touched) > 20:
            out.append(f"- …and {len(r.platform_touched) - 20} more")
        out.append("")

    if r.vendor:
        out += ["### Vendored upstreams", "",
                "| upstream | locked → current | behind | adopted paths changed |",
                "|---|---|---:|---|"]
        for v in r.vendor:
            paths = (", ".join(f"`{p['path']}`" for p in v["paths"][:3]) or "—")
            if len(v["paths"]) > 3:
                paths += f" +{len(v['paths']) - 3}"
            behind = v["commits_behind"] if v["commits_behind"] >= 0 else "?"
            out.append(f"| `{v['id']}` | {v['locked'] or '—'} → {v['current']} | "
                       f"{behind} | {paths} |")
        out.append("")
        affected = sorted({o for v in r.vendor for p in v["paths"] for o in p["ours"]})
        if affected:
            out += ["Files of ours to re-read against upstream:", ""]
            out += [f"- `{f}`" for f in affected]
            out.append("")

    out += ["---",
            (f"<sub>{len(r.files)} file(s) · loop readiness {r.readiness_score}/100 · "
            f"`{r.commit[:8]}` · generated by `pf pr report`</sub>")]
    return "\n".join(out)


# ------------------------------------------------------------------ store ----
def report_dir(root: Path) -> Path:
    return Path(root) / "data" / "pr"


def save(root: str | Path, r: PRReport) -> Path:
    d = report_dir(Path(root))
    d.mkdir(parents=True, exist_ok=True)
    name = f"{r.number}.json" if r.number else f"branch-{r.branch.replace('/', '-')}.json"
    p = d / name
    # The rendered comment is stored alongside the data. Re-rendering it later
    # from a different code version would show something other than what was
    # actually posted on the PR, and the record is only worth keeping if it is
    # the record.
    payload = r.to_dict()
    payload["markdown"] = markdown(r)
    p.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return p


def load_all(root: str | Path) -> list[dict[str, Any]]:
    """Every recorded report, newest first. What the UI's PR view reads."""
    d = report_dir(Path(root))
    if not d.exists():
        return []
    out = []
    for f in d.glob("*.json"):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return sorted(out, key=lambda r: r.get("generated_at", ""), reverse=True)


def pr_number_from_env() -> int:
    """GitHub Actions puts the number in GITHUB_REF (`refs/pull/<n>/merge`)."""
    for key in ("PR_NUMBER", "GITHUB_PR_NUMBER"):
        if os.environ.get(key, "").isdigit():
            return int(os.environ[key])
    ref = os.environ.get("GITHUB_REF", "")
    parts = ref.split("/")
    if len(parts) > 2 and parts[1] == "pull" and parts[2].isdigit():
        return int(parts[2])
    return 0
