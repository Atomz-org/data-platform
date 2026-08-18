"""Mechanical quality score for the reporting layer.

The dashboard loop terminates because most of the bar is checkable. This module
is that check. Everything here is a rule that can be decided by reading files —
judgement questions belong in the `dashboard-loop` skill's critique list, not
here, because a score that encodes taste stops being a score.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Severity = Literal["error", "warning", "info"]

HEX = re.compile(r"#[0-9a-fA-F]{6}\b")
AVG_RATIO = re.compile(r"\bavg\s*\(\s*(aov|[a-z_]*_ratio|[a-z_]*_rate|[a-z_]*_share)\s*\)",
                       re.I)
DUAL_AXIS = re.compile(r"y2\s*=", re.I)
PIE = re.compile(r"<\s*(Pie|Donut)Chart", re.I)
COMPONENT = re.compile(r"<\s*(BigValue|LineChart|BarChart|ScatterPlot|DataTable|"
                       r"AreaChart|Histogram|Heatmap|Sankey)", re.I)
SQL_BLOCK = re.compile(r"```sql\s+(\w+)")
METRIC_REF = re.compile(r"\$\{metrics_(\w+)\}")


@dataclass(frozen=True)
class Finding:
    severity: Severity
    rule: str
    page: str
    message: str

    def __str__(self) -> str:
        mark = {"error": "ERROR", "warning": "WARN ", "info": "INFO "}[self.severity]
        return f"{mark} [{self.rule}] {self.page}: {self.message}"


def audit(project_dir: str | Path) -> tuple[int, list[Finding]]:
    """Score 0-100 and the findings behind it."""
    root = Path(project_dir) / "reporting"
    findings: list[Finding] = []
    if not root.exists():
        return 0, [Finding("error", "no-reporting", "-",
                           "no reporting/ — scaffold with `--with evidence` or "
                           "run `pf report build`")]

    metrics = {f.stem for f in (root / "queries" / "metrics").glob("*.sql")} \
        if (root / "queries" / "metrics").exists() else set()
    pages = sorted((root / "pages").rglob("*.md")) if (root / "pages").exists() else []

    if not metrics:
        findings.append(Finding("error", "no-metrics", "-",
                                "no compiled metrics; the semantic layer has none "
                                "or `pf report build` has not run"))
    if not pages:
        findings.append(Finding("error", "no-pages", "-", "no pages"))

    covered: set[str] = set()

    for page in pages:
        rel = str(page.relative_to(root))
        text = page.read_text()

        refs = set(METRIC_REF.findall(text))
        covered |= refs

        for ref in refs - metrics:
            findings.append(Finding("error", "unknown-metric", rel,
                                    f"references `{ref}`, which has no compiled metric"))

        if not text.lstrip().startswith("---"):
            findings.append(Finding("error", "no-frontmatter", rel,
                                    "no frontmatter; the page has no title"))

        if AVG_RATIO.search(text):
            findings.append(Finding("error", "avg-of-ratio", rel,
                                    "averages a ratio metric — re-divide the carried "
                                    "numerator and denominator instead"))

        if DUAL_AXIS.search(text):
            findings.append(Finding("error", "dual-axis", rel,
                                    "dual-axis chart; use two charts or index to a "
                                    "common base"))

        stray = list(HEX.findall(text))
        if stray:
            findings.append(Finding("warning", "unvalidated-colour", rel,
                                    f"hard-coded hex {stray[:3]} — the theme palette "
                                    f"is validated, an inline value is not"))

        if PIE.search(text):
            findings.append(Finding("warning", "pie-chart", rel,
                                    "pie/donut: use a bar chart unless there are "
                                    "three slices or fewer"))

        charts = COMPONENT.findall(text)
        if len(charts) > 8:
            findings.append(Finding("warning", "chart-wall", rel,
                                    f"{len(charts)} components on one page; a page "
                                    f"answers one question"))

        body = text.split("---", 2)[-1].strip()
        first = next((ln for ln in body.splitlines()
                      if ln.strip() and not ln.startswith(("#", "<", "`"))), "")
        if len(first) < 40:
            findings.append(Finding("warning", "no-context", rel,
                                    "no context sentence under the title — a reader "
                                    "cannot tell what is included or excluded"))

        named = SQL_BLOCK.findall(text)
        if len(named) != len(set(named)):
            findings.append(Finding("error", "duplicate-query-name", rel,
                                    "two sql blocks share a name; the later silently "
                                    "shadows the earlier"))

    for orphan in sorted(metrics - covered):
        findings.append(Finding("info", "metric-unused", "-",
                                f"metric `{orphan}` appears on no page"))

    errors = sum(1 for f in findings if f.severity == "error")
    warns = sum(1 for f in findings if f.severity == "warning")
    score = max(0, 100 - errors * 20 - warns * 5)
    return score, findings
