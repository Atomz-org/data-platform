"""The three LLM-backed loop agents.

Each takes deterministic evidence gathered by the loop body and returns a typed
verdict. The graph does the retrieval; the model does the judgement. That split
is what keeps these calls small — a triage prompt carries the failing node and
its lineage neighbourhood, not the repository.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from pf.agents.base import AGENTS, cached_prefix, call

# ------------------------------------------------------------- schemas -----
_UNDERSTANDING = Field(
    default="",
    description="In one or two sentences, what you took the input to be and what "
                "question you are answering. Written for the trace log a person "
                "reads when the verdict is wrong.")


class Diagnosis(BaseModel):
    understanding: str = _UNDERSTANDING
    root_cause: Literal["upstream_data", "model_logic", "stale_source",
                        "test_too_strict", "unknown"]
    summary: str = Field(description="One sentence a data engineer can act on.")
    evidence: str = Field(description="What in the input supports this classification.")
    suggested_fix: str
    confidence: Literal["low", "medium", "high"]
    escalate: bool = Field(description="True if a human must decide before any fix.")


class AnomalyReport(BaseModel):
    understanding: str = _UNDERSTANDING
    headline: str = Field(description="One line for STATE.md.")
    severity: Literal["info", "warn", "critical"]
    likely_cause: str
    ignorable: bool = Field(description="True if this is expected noise, not a problem.")


class MetricProposal(BaseModel):
    metric_name: str = Field(description="snake_case, e.g. net_revenue_retention")
    label: str
    metric_type: Literal["simple", "ratio", "derived", "cumulative"]
    measure_or_expr: str = Field(description="Measure name, or the derived expression.")
    filter_expression: str = Field(description="MetricFlow filter, or empty string.")
    rationale: str = Field(description="Why this metric, and what question it answers.")


class MetricProposals(BaseModel):
    understanding: str = _UNDERSTANDING
    proposals: list[MetricProposal]
    summary: str


class FixPatch(BaseModel):
    """One whole file, rewritten. See `pf.loops.actions.Proposal` for why whole."""

    understanding: str = _UNDERSTANDING
    path: str = Field(description="The project-relative path of the file shown, unchanged.")
    content: str = Field(description="The complete new contents of that file.")
    title: str = Field(description="Pull request title, imperative, under 70 chars.")
    rationale: str = Field(description="What changed and why, for the reviewer.")
    safe: bool = Field(description="False if the change needs a decision a human "
                                   "must make first — then nothing is proposed.")


# ------------------------------------------------------------- agents ------
def triage_failures(root: Path, group: str, project: str,
                    failures: list[dict], lineage: str) -> Diagnosis | None:
    """Classify failing dbt nodes. Lineage comes from the graph, not from grep."""
    cfg = AGENTS["test_failure_triage"]
    body = "\n".join(
        f"- {f['unique_id']} [{f['status']}]: {(f.get('message') or '')[:400]}"
        for f in failures[:10])
    user = (
        "<failing_nodes>\n" + body + "\n</failing_nodes>\n\n"
        "<lineage_neighbourhood>\n" + lineage[:4000] + "\n</lineage_neighbourhood>\n\n"
        "Classify the root cause. The four classes need different responses, so be "
        "decisive:\n"
        "- upstream_data: the source landed bad or incomplete data\n"
        "- model_logic: the SQL is wrong (a join fanned out, a filter is inverted)\n"
        "- stale_source: the data is fine but old; a re-run fixes it\n"
        "- test_too_strict: the test encodes an assumption that is no longer true\n\n"
        "A test that fails because the test is wrong is a real outcome — say so "
        "rather than proposing a change to the model to satisfy it."
    )
    parsed, _ = call(cfg, system=cached_prefix(root, group, project, cfg), user=user,
                     output_format=Diagnosis, group=group, project=project)
    return parsed


def assess_anomaly(root: Path, group: str, project: str,
                   monitor_rows: list[dict]) -> AnomalyReport | None:
    """Turn raw monitor rows into one prioritised line, or mark them as noise."""
    cfg = AGENTS["freshness_triage"]
    body = "\n".join(
        f"- {r['resource']}.{r['column_name']} [{r['monitor']}] {r['status']}: "
        f"observed={r.get('observed')} expected={r.get('expected')} "
        f"dev={r.get('deviation_pct')}% — {r.get('message', '')}"
        for r in monitor_rows[:20])
    user = (
        "<monitor_results>\n" + body + "\n</monitor_results>\n\n"
        "These are statistical monitors, not assertions — some deviation is normal. "
        "Decide whether this is a real problem or expected noise (a weekend dip, a "
        "known seasonal pattern, a small-sample table). Set ignorable=true when it "
        "is noise; a monitor that always warns and is never acted on is worse than "
        "no monitor."
    )
    parsed, _ = call(cfg, system=cached_prefix(root, group, project, cfg), user=user,
                     output_format=AnomalyReport, group=group, project=project)
    return parsed


def propose_metrics(root: Path, group: str, project: str,
                    gaps: list[str], mart_detail: str) -> MetricProposals | None:
    """Propose MetricFlow definitions for marts nothing measures."""
    cfg = AGENTS["metric_gap_proposer"]
    user = (
        "<uncovered_marts>\n" + "\n".join(f"- {g}" for g in gaps) + "\n</uncovered_marts>\n\n"
        "<mart_columns>\n" + mart_detail[:4000] + "\n</mart_columns>\n\n"
        "Propose MetricFlow metrics for these marts. Rules:\n"
        "- The mart declares the grain; the metric declares the aggregation policy "
        "(which statuses count, which timestamp, which filters).\n"
        "- Prefer composing existing metrics (ratio, derived) over recomputing.\n"
        "- Only propose metrics the columns actually support. If a mart genuinely "
        "does not need one, return no proposal for it and say why in the summary."
    )
    parsed, _ = call(cfg, system=cached_prefix(root, group, project, cfg), user=user,
                     output_format=MetricProposals, group=group, project=project)
    return parsed




def draft_fix(root: Path, group: str, project: str, *, diagnosis: Diagnosis,
              rel_path: str, current: str, lineage: str) -> FixPatch | None:
    """Turn a diagnosis into a whole-file rewrite. Transcription, not judgement.

    Only two root causes are eligible — `model_logic` and `test_too_strict` —
    because those are the two where the fix is a file in this repository.
    `upstream_data` and `stale_source` are fixed elsewhere, and drafting a
    model change for them is how a loop papers over a data problem.
    """
    cfg = AGENTS["fix_drafter"]
    nl = "\n"
    user = (
        "<diagnosis>" + nl
        + f"root_cause: {diagnosis.root_cause}{nl}summary: {diagnosis.summary}{nl}"
        + f"evidence: {diagnosis.evidence}{nl}suggested_fix: {diagnosis.suggested_fix}{nl}"
        + "</diagnosis>" + nl + nl
        + f'<file path="{rel_path}">{nl}{current[:12000]}{nl}</file>{nl}{nl}'
        + "<lineage_neighbourhood>" + nl + lineage[:3000] + nl + "</lineage_neighbourhood>"
        + nl + nl
        + "Rewrite the file to implement the suggested fix and nothing else. Rules:" + nl
        + "- Return the whole file. Keep every line you are not changing byte-identical." + nl
        + "- The mart's grain and the metric definitions downstream must not change; "
          "if the fix would change them, set safe=false and explain." + nl
        + "- A test_too_strict fix edits the test's config or expression, never the "
          "model, and never deletes the test." + nl
        + "- No new sources, no new columns the lineage does not already show." + nl
        + "- If you are not sure the rewrite compiles, set safe=false."
    )
    parsed, _ = call(cfg, system=cached_prefix(root, group, project, cfg), user=user,
                     output_format=FixPatch, group=group, project=project)
    return parsed
