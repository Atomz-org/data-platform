"""What every model is told before it writes a metric, and the rules each
harness follows — the model-agnostic half of the framework.

The prompt embeds the contract's JSON schema rather than describing it, so
the text an agent reads and the class that judges its answer cannot drift
apart. The directives are per *harness*, not per vendor, matching how
AGENTS.md scopes every other rule here; they are rendered into docs/AIDF.md
and read by `pf govern prompt`.
"""

from __future__ import annotations

import json
from collections.abc import Iterable

from pf.aidf.schemas import json_schema

TEMPLATE = """\
You are acting as an autonomous metric generation sub-agent for {group}/{project}.
Target Mart: {mart_name}
Target Metric: {metric_name}
SQL dialect: {dialect}
Approved Catalog Columns: {approved_columns}

Instructions:
1. Generate an aggregation calculation satisfying the MartMetricContract schema below.
2. The SQL must be a pure SELECT projection or aggregation expression: no DDL, no DML,
   no system catalogues, no file-reading functions, no SELECT *.
3. Use only columns present in the Approved Catalog Columns list, and list every one you
   use in dependent_columns.
4. Do not include credentials, secrets, IP addresses, e-mail addresses or personal data.
5. Emit your final result strictly as one raw JSON object matching the schema. No prose.

MartMetricContract JSON schema:
{schema}
"""

#: How each harness scope applies the framework. Keyed by scope, as AGENTS.md
#: §0 defines them, because the rules depend on what a tool can do and not on
#: whose model is behind it.
DIRECTIVES: dict[str, str] = {
    "session": (
        "Produce metric and semantic-model proposals as MartMetricContract / SemanticModelContract JSON and "
        "submit them through `pf govern evaluate` (or the `govern_metric` MCP tool); never write under "
        "`governance/metrics/` by hand. Run `pf dora audit` before claiming an entity is compliant."
    ),
    "autonomous": (
        "Same as a session, with nobody to ask: a REJECT is final for this run (fix the payload, never the "
        "rule), an ESCALATED outcome waits for `pf provenance approve`, and a CIRCUIT_BROKEN outcome ends the "
        "run — say so in the issue or the pull request."
    ),
    "inline": (
        "When completing SQL inside a metric definition, reference only columns the file already names or the "
        "mart's kg/architecture.md lists; never emit DDL or DML; never touch provenance/, gate.yaml, LOOP.md "
        "or .github/. Leave a `NOTE(memory):` for the session that commits if the catalogue disagrees."
    ),
    "local-model": (
        "Before generating SQL, emit a verification block listing the tables and columns you intend to "
        "reference and confirm each is in the Approved Catalog Columns. Reason step by step, then emit only "
        "the JSON object."
    ),
    "ci-glue": (
        "Generate integration and workflow steps with `uv run` / `uv sync` / `uvx` only; never `pip install` "
        "inside an application loop. Tools that are commands (prowler, trivy, guardrails) are installed "
        "isolated, never added to the workspace lockfile."
    ),
}


def metric_prompt(group: str, project: str, mart_name: str, metric_name: str, approved_columns: Iterable[str],
                  dialect: str = "duckdb") -> str:
    cols = ", ".join(sorted(approved_columns)) or "(no catalogue available — the validator will report catalog: absent)"
    return TEMPLATE.format(group=group, project=project, mart_name=mart_name, metric_name=metric_name,
                           dialect=dialect, approved_columns=cols,
                           schema=json.dumps(json_schema("mart_metric"), indent=2, sort_keys=True))
