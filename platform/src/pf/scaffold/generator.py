"""Scaffold groups and projects. No external template engine — templates are
plain strings with `{{token}}` substitution, so `pf new-project` works from a
bare checkout.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

TEMPLATE_DIR = Path(__file__).parent / "templates"


def render(text: str, ctx: dict[str, Any]) -> str:
    def sub(m: re.Match) -> str:
        key = m.group(1).strip()
        return str(ctx.get(key, m.group(0)))
    return re.sub(r"\{\{\s*([a-z_]+)\s*\}\}", sub, text)


def write(path: Path, content: str, ctx: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(content, ctx))
    return path


DEFAULT_CLASSES = {
    "b2b_saas": ["Customer", "Organization", "Subscription", "Payment", "Usage", "Product"],
    "ecommerce": ["Customer", "Order", "Payment", "Refund", "Product", "Location"],
    "marketplace": ["Customer", "Organization", "Order", "Payment", "Product"],
    "fintech": ["Customer", "Organization", "Contract", "Payment", "Refund", "Currency"],
}


# ------------------------------------------------------------------ group --
def new_group(root: Path, group: str, domain: str = "b2b_saas") -> list[Path]:
    gdir = root / "groups" / group
    if gdir.exists():
        raise FileExistsError(f"group '{group}' already exists at {gdir}")
    classes = DEFAULT_CLASSES.get(domain, DEFAULT_CLASSES["b2b_saas"])
    ctx = {"group": group, "domain": domain,
           "classes_yaml": "\n".join(f"  - {c}" for c in classes),
           "tools_yaml": _default_tools_yaml()}
    created = [
        write(gdir / "tools.yaml", GROUP_TOOLS, ctx),
        write(gdir / "air.yaml", GROUP_AIR, ctx),
        write(gdir / "ontology" / "instance.yaml", GROUP_INSTANCE, ctx),
        write(gdir / "CLAUDE.md", GROUP_CLAUDE, ctx),
        write(gdir / ".claude-plugin" / "marketplace.json", GROUP_MARKETPLACE, ctx),
        write(gdir / ".claude" / "skills" / "README.md", GROUP_SKILLS_README, ctx),
        write(gdir / "shared" / "transform" / "dbt_project.yml", GROUP_SHARED_DBT, ctx),
        write(gdir / "shared" / "transform" / "macros" / "normalize_currency.sql", GROUP_MACRO, ctx),
        write(gdir / "evals" / "README.md", GROUP_EVALS, ctx),
    ]
    (gdir / "projects").mkdir(parents=True, exist_ok=True)
    (gdir / "kg").mkdir(parents=True, exist_ok=True)
    return created


def _default_tools_yaml() -> str:
    """The `tools:` block a new group starts with, read from the registry.

    Asked of the installed tools rather than hardcoded, so registering a tool
    stays the only step — the same reason `pf tool list` and the UI do not name
    one either. A discovery failure yields an empty block: a group scaffolded
    with nothing enabled is recoverable with `pf tool enable`, whereas a
    scaffold that raises leaves half a group on disk.
    """
    try:
        from pf.tools import all_tools
        names = sorted(n for n, t in all_tools().items()
                       if t.default_enabled and "group" in t.scope)
    except Exception:  # noqa: BLE001 — a broken plugin must not block scaffolding
        names = []
    if not names:
        return " {}"
    return "\n" + "\n".join(f"  {n}:\n    enabled: true" for n in names)


# ---------------------------------------------------------------- project --
def new_project(root: Path, group: str, project: str, is_rollup: bool = False,
                sisters: list[str] | None = None) -> list[Path]:
    """Scaffold one project.

    The `hooks.PreToolUse` block in PROJECT_SETTINGS is load-bearing, not
    boilerplate: it is the only thing that applies `gate.yaml` to an agent's
    edits inside this project. Projects created before it was templated here had
    to be patched by hand, which is exactly the drift the gate exists to prevent.
    Callers should follow up with `pf kg build` so the project has a graph from
    day one — see `cmd_new_project`.
    """
    gdir = root / "groups" / group
    if not gdir.exists():
        raise FileNotFoundError(f"group '{group}' does not exist — run `pf new-group {group}` first")
    pdir = gdir / "projects" / project
    if pdir.exists():
        raise FileExistsError(f"project '{project}' already exists at {pdir}")

    module = project.replace("-", "_")
    sisters = sisters or []
    ctx = {
        "group": group, "project": project, "module": module,
        "sisters_py": ", ".join(f'"{s.replace("-", "_")}": "../{s}/data/{s.replace("-", "_")}.duckdb"'
                                for s in sisters),
        "sister_list": ", ".join(sisters) or "none",
        "deny_siblings": ", ".join(
            f'"Read(../{s}/**)"' for s in sisters) or '"Read(../*/src/**)"',
    }

    created = [
        write(pdir / "CLAUDE.md", PROJECT_CLAUDE, ctx),
        write(pdir / ".claude" / "settings.json", PROJECT_SETTINGS, ctx),
        write(pdir / "pyproject.toml", PROJECT_PYPROJECT, ctx),
        write(pdir / "src" / module / "__init__.py", '"""{{project}} — business logic only."""\n', ctx),
        write(pdir / "src" / module / "definitions.py",
              ROLLUP_DEFS if is_rollup else PROJECT_DEFS, ctx),
        write(pdir / "src" / module / "sources" / "__init__.py",
              '"""Annotated dlt sources."""\n', ctx),
        write(pdir / "src" / module / "defs" / "__init__.py",
              '"""Extra Dagster assets collected by the factory."""\n', ctx),
        write(pdir / "src" / module / "agents" / "__init__.py",
              '"""Project-specific agent logic."""\n', ctx),
        write(pdir / "transform" / "dbt_project.yml", PROJECT_DBT, ctx),
        write(pdir / "transform" / "profiles.yml", render_profiles(module), ctx),
        write(pdir / "transform" / "packages.yml", PROJECT_PACKAGES, ctx),
        write(pdir / "transform" / "models" / "staging" / ".gitkeep", "", ctx),
        write(pdir / "transform" / "models" / "marts" / ".gitkeep", "", ctx),
        write(pdir / "transform" / "models" / "semantic" / ".gitkeep", "", ctx),
        write(pdir / "transform" / "models" / "utils" / "metricflow_time_spine.sql", TIME_SPINE, ctx),
        write(pdir / "transform" / "models" / "utils" / "_utils__models.yml", TIME_SPINE_YML, ctx),
        write(pdir / ".dlt" / "config.toml", PROJECT_DLT_CONFIG, ctx),
        write(pdir / "evals" / "cases" / "README.md", PROJECT_EVALS, ctx),
        write(pdir / "decisions" / "README.md", PROJECT_DECISIONS, ctx),
        write(pdir / ".memory" / "notes" / "README.md", PROJECT_MEMORY, ctx),
        write(pdir / "kg" / "context_card.md", EMPTY_CARD, ctx),
        write(pdir / "tools.yaml", PROJECT_TOOLS, ctx),
    ]
    for d in ("data", "kg", "contracts"):
        (pdir / d).mkdir(parents=True, exist_ok=True)
    return created


# ================================================================ templates ==
GROUP_AIR = """\
# Which AI controls the {{group}} family commits to.
#
# Read, not generated — `governance/air-register.md` is the generated half.
# Control ids come from whichever catalogues are registered; `pf air catalogues`
# lists them, `pf air controls` lists the ids, `pf air show <id>` explains one.
#
# Declared here means declared for **every sister project** in {{group}}. A
# project may add to `baseline` in its own air.yaml; it cannot remove from it.
# The way to drop a control is `accepted:`, which requires a reason and an owner.
#
#   pf air coverage {{group}} <project>    # what this entity enforces today
#   pf air baseline {{group}} --suggest    # the controls that already pass
#   pf air gate {{group}} <project>        # blocks on a failing commitment
#
# `baseline` starts empty on purpose. A scaffolder that pre-commits a family to
# a set of controls produces commitments nobody made, and the first gate run
# fails on a decision never taken. Fill it from `--suggest`, which proposes only
# what already passes — a ratchet against regression rather than a wall of work.
version: 1

# Where this family sits in the catalogue's taxonomy, if it declares one.
# `pf air catalogues` names the corpus; its deployment-model data file lists the
# vocabulary. Free-form until then.
profile: {}

# Controls this family commits to. `pf air gate` blocks the merge when one of
# these is failing; everything outside this list is reported and advisory.
baseline: []

# Controls consciously not taken. `reason` and `owner` are both required: an
# acceptance without a reason is a gap with better formatting, and one without
# an owner is a decision nobody can be asked about.
#
# accepted:
#   - control: <id>
#     reason: >
#       Why this family does not take it, in a sentence somebody can disagree with.
#     owner: someone@example.com
#     review_by: 2027-01-01
accepted: []
"""

GROUP_TOOLS = """\
# Which platform tools this group runs. `pf tool list` shows what is available.
#
# Enabled here means enabled for **every sister project** in {{group}} — that is
# the point of a group. Sisters share infrastructure and differ only in business
# logic, so "we review dbt changes with Recce" is decided once for the family.
# A project can override any key in its own tools.yaml, including turning a tool
# off, which is the escape hatch for an entity the decision does not fit.
#
#   pf tool enable recce {{group}}              # the whole family
#   pf tool enable recce {{group}} <project>    # one entity
#
# A tool that is enabled but not installed on this machine is skipped with a
# note, never a failure: enabling is a decision about the project, installing is
# a fact about the laptop.
#
# What is listed below is what the installed tools declare as a default for a
# new family, not a fixed set. Turn any of it off; it is your file now.
version: 1
tools:{{tools_yaml}}
"""

PROJECT_TOOLS = """\
# Tools for {{project}}, merged over groups/{{group}}/tools.yaml.
#
# Set `enabled: false` here to opt out of something the group turned on. Config
# dicts deep-merge, so overriding one key (a port, say) keeps the rest.
#
#   pf tool list {{group}} {{project}}      # what is on, and where it came from
#   pf tool doctor {{group}} {{project}}    # why a tool is not doing anything
version: 1
tools: {}
"""

GROUP_INSTANCE = """\
# Ontology instance for {{group}} — which platform classes this group models.
# Validated against platform/src/pf/ontology/concepts.yaml by `pf check`.
group: {{group}}
domain: {{domain}}
classes:
{{classes_yaml}}
shared_sources: []
"""

GROUP_CLAUDE = """\
# {{group}} — group context

@kg/group_card.md

Sister projects under `projects/` share this ontology instance, the conformed
dimensions in `shared/transform`, and group-level metrics. They have **separate
warehouses and run in parallel**.

## Business rules the graph cannot encode
<!-- Add durable, entity-wide rules here. Keep it short: this loads every session. -->
- (none yet)

## Cross-entity work
Only the `<group>-rollup` project may read sister data, and only via ATTACH READ_ONLY.
Never read a sister project's files from another project.
"""

GROUP_MARKETPLACE = """\
{
  "name": "{{group}}",
  "owner": { "name": "{{group}}" },
  "plugins": [
    { "name": "{{group}}-group", "source": "./.claude", "description": "{{group}} group skills" }
  ]
}
"""

GROUP_SKILLS_README = """\
# {{group}} group skills

Skills specific to this group's business, shared by every sister project.
Infra skills come from `platform/toolkits` — do not duplicate them here.

Put a skill here when it encodes {{group}}'s domain knowledge (a reconciliation
procedure, a regulatory workflow, a naming rule the ontology cannot express).
"""

GROUP_SHARED_DBT = """\
name: '{{group}}_shared'
version: '1.0.0'
config-version: 2
profile: '{{group}}_shared'
macro-paths: ["macros"]
"""

GROUP_MACRO = """\
{% macro normalize_currency(amount_col, currency_col, target='USD') %}
    -- Applied automatically wherever a money_amount / currency_code pair is
    -- annotated. Rates come from the group's fx seed; contracts are struck at
    -- signature and never re-struck.
    case
        when {{ currency_col }} = '{{ target }}' then {{ amount_col }}
        else {{ amount_col }} * coalesce(fx.rate, 1.0)
    end
{% endmacro %}
"""

PROJECT_CLAUDE = """\
# {{project}} — project context

@kg/context_card.md

Group: `{{group}}`. The sister roster lives in the group card above —
do not read a sister's files from here.

## Business rules the graph cannot encode
<!-- Domain facts an agent cannot derive from the models. Keep it tight. -->
- (none yet)

## The semantic stack
Vocabulary is platform-wide and already loaded in this project's graph before any
data exists — `kg_search` finds concepts, relations and policies on day one.

| Ask | Command |
|---|---|
| What relates to what | `pf semantic topology` |
| What must hold, and what enforces it | `pf semantic policy` |
| BI / WrenAI projection | `pf semantic mdl {{group}} {{project}}` → `mdl/mdl.json` |
| Re-run every generated artefact | `pf bootstrap {{group}} {{project}}` |

A foreign key must be declared with `links={"col": "SomeClass"}`, and the topology
must already relate the two classes — that binding is what makes join conditions
derivable rather than guessed. `pf check` fails on an undeclared join.

## Conventions
- Every dlt resource is annotated (`@annotate`) before any model is written.
- Marts declare `meta.grain`; the semantic layer owns aggregation policy.
- Ask the graph before reading files: `kg_search`, `kg_neighbors`, `kg_path`.
- Run `impact_analysis` before changing a column, a model or a metric.
"""

PROJECT_SETTINGS = """\
{
  "extraKnownMarketplaces": {
    "platform": { "source": { "source": "../../../../platform" } },
    "{{group}}": { "source": { "source": "../.." } }
  },
  "enabledPlugins": [
    "platform-init@platform",
    "dlt-ingest@platform",
    "dlt-quality@platform",
    "dlt-explore@platform",
    "duckdb-ops@platform",
    "dbt-modeling@platform",
    "dbt-semantic@platform",
    "dbt-testing@platform",
    "dbt-govern@platform",
    "dagster-orchestrate@platform",
    "python-standards@platform",
    "power-tools@platform",
    "{{group}}-group@{{group}}"
  ],
  "permissions": {
    "deny": [{{deny_siblings}}, "Read(../../../*/projects/**)",
      "Read(./.env)", "Read(./.env.*)",
      "Read(**/secrets.toml)", "Read(**/.dlt/secrets.toml)",
      "Read(**/credentials/**)"],
    "ask": ["Bash(git push:*)", "Bash(gh pr create:*)"],
    "allow": [
      "Bash(uv run pf:*)",
      "Bash(dbt parse:*)", "Bash(dbt ls:*)", "Bash(dbt build:*)", "Bash(dbt test:*)",
      "Bash(mf query:*)", "Bash(mf list:*)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "uv run python ../../../../platform/hooks/pre_tool_use.py"
          }
        ]
      }
    ]
  }
}
"""

PROJECT_PYPROJECT = """\
[project]
name = "{{module}}"
version = "0.1.0"
requires-python = ">=3.11,<3.13"
dependencies = ["pf"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{{module}}"]
"""

PROJECT_DEFS = '''\
"""Dagster entry point. The platform factory assembles everything —
never scaffold a raw Definitions object here.

`project_dir` is derived from __file__ so the definitions load identically from
`dagster dev`, a code location, or an ad-hoc python -c. Never rely on cwd.
"""

from pathlib import Path

from pf.runtime.dagster_runtime import build_definitions

PROJECT_DIR = Path(__file__).resolve().parents[2]

defs = build_definitions(
    group="{{group}}",
    project="{{project}}",
    project_dir=PROJECT_DIR,
)
'''

ROLLUP_DEFS = '''\
"""Cross-entity roll-up. Attaches sister warehouses READ_ONLY."""

from pathlib import Path

from pf.runtime.dagster_runtime import build_definitions

PROJECT_DIR = Path(__file__).resolve().parents[2]

defs = build_definitions(
    group="{{group}}",
    project="{{project}}",
    project_dir=PROJECT_DIR,
    sisters={ {{sisters_py}} },
)
'''

PROJECT_DBT = """\
name: '{{module}}'
version: '1.0.0'
config-version: 2
profile: '{{module}}'

model-paths: ["models"]
# Platform cleaning macros load as root-project macros, not as a package:
# `pf_clean` dispatches to its `clean_*` siblings unqualified, and dbt namespaces
# package macros, so a package install fails on the inner dispatch.
#
# dbt-snowflake is the cross-database function layer: `{{ sf_iff(...) }}` and its
# siblings compile to whatever the *target* adapter understands, so one model
# runs on DuckDB in development and Snowflake in production. `pf dialect` lists
# what is covered. Adding a sibling toolkit (dbt-bigquery) means adding its
# macros directory here.
macro-paths:
  - "macros"
  - "../../../../../platform/dbt/macros"
  - "../../../../../platform/toolkits/dbt-snowflake/macros"
seed-paths: ["seeds"]
test-paths: ["tests"]
target-path: "target"

models:
  {{module}}:
    staging:
      +materialized: view
      +schema: staging
    marts:
      +materialized: table
      +schema: marts
"""

#: The dbt targets every project gets, as data rather than as one literal block.
#:
#: Written this way because targets are the part of a project that varies most
#: between the repositories this platform adopts, and each one is wanted
#: individually: `pf align` checks that a named target exists and has the
#: expected warehouse type, the `dbt wiring` bootstrap step appends a target a
#: project predates, and a capability replaces `prod` with a real warehouse
#: without touching the other three. All four of those need one target, and a
#: single YAML literal can only give them all four.
#:
#: Every default here is DuckDB, which is the whole point: a developer must be
#: able to build the entire project on a laptop with no credentials, or they
#: stop building it. Production is declared per project — `pf capability-add
#: <group> <project> snowflake` rewrites this `prod` entry.
PROJECT_TARGETS: dict[str, dict[str, object]] = {
    "dev":  {"type": "duckdb", "path": "{{ env_var('PF_DUCKDB_PATH') }}", "threads": 4},
    "ci":   {"type": "duckdb", "path": "{{ env_var('PF_DUCKDB_PATH') }}", "threads": 8},
    "prod": {"type": "duckdb", "path": "{{ env_var('PF_DUCKDB_PATH') }}", "threads": 8},
    # Recce compares two *built* states, so there has to be somewhere to build
    # the second one. Same file, different schema: a separate database would mean
    # loading the seeds twice and would put the two states out of reach of a
    # single connection. The per-layer `+schema:` config appends to this, so
    # staging lands in `base_staging` and never collides with `main_staging`.
    "base": {"type": "duckdb", "path": "{{ env_var('PF_DUCKDB_PATH') }}",
             "schema": "base", "threads": 4},
}


def render_target(name: str, spec: dict[str, object], indent: str = "    ") -> str:
    """One dbt output block. The unit `pf align` checks and bootstrap appends."""
    lines = [f"{indent}{name}:"]
    for key, value in spec.items():
        if isinstance(value, bool):
            # Before booleans appeared here every value was a string or an int,
            # and Python's `True` reached the file verbatim. YAML 1.1 does read
            # it as a boolean, so nothing was broken — but a generated file that
            # nobody can copy an idiom from is a generated file people edit by
            # hand, and `secure: True` beside `threads: 8` reads as a mistake.
            rendered: object = "true" if value else "false"
        elif isinstance(value, str) and "{{" in value:
            rendered = f'"{value}"'
        else:
            rendered = value
        lines.append(f"{indent}  {key}: {rendered}")
    return "\n".join(lines) + "\n"


def replace_target(text: str, name: str, spec: dict[str, object]) -> tuple[str, bool]:
    """Swap one output block in an existing profiles.yml. Returns (text, changed).

    Text-level, and deliberately not a YAML round-trip. `yaml.safe_dump` of a
    parsed profile is a *different file*: it loses every comment, and the
    comments in these files are load-bearing — acme-eu's `base` target carries
    six lines explaining why a diff needs a second materialisation, which is the
    kind of thing that gets deleted once and re-learned expensively.

    It is also not a whole-file regeneration. That was tried: rewriting
    acme-eu's profiles.yml from the template silently dropped
    `extensions: [httpfs, json]` from two targets, because the template has no
    `extensions` key and never did. Anything a project added by hand to a target
    this function is not replacing survives untouched, byte for byte.

    The block is bounded by indentation: everything more-indented than the
    `<name>:` line belongs to it, and the first line at or above that indent
    ends it. A comment sitting at the parent indent — the usual place to put one
    — therefore belongs to the *next* target and is left where it is.
    """
    lines = text.splitlines()
    head = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == f"{name}:" and line != stripped:
            head, indent = i, line[: len(line) - len(line.lstrip())]
            break
    if head is None:
        return text, False

    end = head + 1
    while end < len(lines):
        line = lines[end]
        if line.strip() and len(line) - len(line.lstrip()) <= len(indent):
            break
        end += 1

    block = render_target(name, spec, indent).rstrip("\n").splitlines()
    if lines[head:end] == block:
        return text, False
    return "\n".join(lines[:head] + block + lines[end:]) + "\n", True


def target_type(text: str, name: str) -> str:
    """The `type:` of one output, or "" if the profile has no such target."""
    import yaml

    try:
        doc = yaml.safe_load(text) or {}
    except yaml.YAMLError:
        return ""
    for value in doc.values():
        if isinstance(value, dict) and isinstance(value.get("outputs"), dict):
            spec = value["outputs"].get(name)
            if isinstance(spec, dict):
                return str(spec.get("type") or "")
    return ""


def render_profiles(module: str, targets: dict[str, dict[str, object]] | None = None) -> str:
    """A whole profiles.yml. `DBT_TARGET` selects; nothing else switches warehouse."""
    targets = PROJECT_TARGETS if targets is None else targets
    head = (f"{module}:\n"
            f"  target: \"{{{{ env_var('DBT_TARGET', 'dev') }}}}\"\n"
            f"  outputs:\n")
    return head + "".join(render_target(n, s) for n, s in targets.items())

PROJECT_PACKAGES = """\
packages:
  - package: dbt-labs/dbt_utils
    version: [">=1.3.0", "<2.0.0"]
"""

PROJECT_DLT_CONFIG = """\
[runtime]
log_level = "WARNING"

[normalize.data_writer]
disable_compression = false
"""

GROUP_EVALS = """\
# Evals for {{group}}

Prompts are code; these are their tests. Cases here cover what the sisters
**share and only share** — the group's ontology instance, its conformed
dimensions, its group-level metrics.

Three tiers run together, and each owns what only it can know:

| Tier | Lives in | Owns |
|---|---|---|
| platform | `platform/toolkits/<toolkit>/evals/` | health checks, and templates |
| **group** | **here** | what every sister in {{group}} agrees on |
| project | `projects/<project>/evals/cases/` | one entity's business logic |

A case belongs here when it would be *wrong for a sister to disagree with it*.
If one sister could legitimately answer differently, it is a project case.

```json
{
  "name": "conformed_customer_grain_is_respected",
  "agent": "metric_gap_proposer",
  "why": "Why this case exists — what breaks without it.",
  "tags": ["conformed"],
  "input": {"gaps": ["..."], "mart_detail": "..."},
  "expect": {"proposals[].metric_type": {"any": {"equals": "ratio"}}}
}
```

    pf evals {{group}} <project>          # contract tier + load every case
    pf evals {{group}} <project> --live   # grade against the real models

Any change to an agent prompt must keep these green.
"""

PROJECT_EVALS = """\
# Evals for {{project}}

Prompts are code; these are their tests.

## Two kinds of case live here

**`generated/`** — written by `pf evals-gen {{group}} {{project}}`. Each toolkit
ships eval *templates*: the shape of a correct judgement, with placeholders where
the table names go. Generation resolves those against this project's knowledge
graph, so the cases name **your** models and **your** columns.

Regenerating overwrites that directory and deletes anything whose template is
gone. Never hand-edit a file in it.

**Everything else in `evals/cases/`** — yours. Cases that encode {{project}}'s own
business rules, which no toolkit could have guessed. This is where the corpus
earns its keep: a restraint case naming the bridge tables that should get no
metric, a triage case for the settlement window only this entity has.

Nothing here is read by a sister, and nothing a sister writes is read here.

## Format

```json
{
  "name": "triage_recognises_our_late_settlement_window",
  "agent": "test_failure_triage",
  "why": "Why this case exists — what breaks in production without it.",
  "tags": ["triage"],
  "input": {"failures": [], "lineage": "..."},
  "expect": {"root_cause": "stale_source", "escalate": false}
}
```

`agent` is one of `test_failure_triage`, `freshness_triage`,
`metric_gap_proposer`. `why` is not decoration — without it a corpus decays into
assertions nobody dares change because nobody remembers whether they were
deliberate.

Keep prose matchers weak (`contains_any`, not exact strings). A case that pins
wording fails on a harmless rewrite, and a suite that cries wolf gets switched
off — which costs more than the case was ever worth.

## Commands

    pf evals-gen {{group}} {{project}}      # (re)ground the toolkit templates
    pf evals {{group}} {{project}}          # contract tier + load every case
    pf evals {{group}} {{project}} --live   # grade against the real models

`--samples N` runs each case N times. A case that passes 4 times in 5 is not
passing and not failing — it is an unstable prompt, which is the most useful
thing this suite can tell you before a prompt change ships.

Any change to an agent prompt must keep these green.
"""

PROJECT_DECISIONS = """\
# Decision log

One ADR per durable decision, explaining *why* — a grain, a metric filter, an
exclusion rule. The knowledge graph indexes these, so `kg_search` finds them.

Name them `ADR-0001-short-title.md`. Never delete one; supersede it.
"""

PROJECT_MEMORY = """\
# Session memory

One lesson per file, one-line summary on top. Written mid-task by agents.

Promotion into `groups/{{group}}/CLAUDE.md` (group-wide) or a platform RULES.md
(universal) is a reviewed, human step — that promotion is what makes the platform
compound instead of accumulating notes nobody reads.
"""


TIME_SPINE = """\
-- Required by MetricFlow for time-based metrics. Platform-standard daily grain.
{{ config(materialized='table') }}
select cast(range as date) as date_day
from range(date '2020-01-01', date '2030-01-01', interval 1 day)
"""

TIME_SPINE_YML = """\
version: 2
models:
  - name: metricflow_time_spine
    description: Daily time spine required by MetricFlow.
    config:
      materialized: table
    time_spine:
      standard_granularity_column: date_day
    columns:
      - name: date_day
        granularity: day
        data_tests: [unique, not_null]
"""


EMPTY_CARD = """\
## {{project}} — data index (not yet built)

This project has no sources, models or metrics. `kg_search` and `query_metrics`
will return nothing until it does.

**Start here:** the `quick-start` skill. In short — scaffold a dlt source
(`find-source`), annotate it (`annotate-source`), run `pf seed {{group}} {{project}}`,
then build staging and marts. This card regenerates itself on every seed.
"""
