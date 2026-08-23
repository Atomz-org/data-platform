"""Capability registry — how a new feature reaches every project.

The platform will keep growing sideways: a GitHub integration, a Slack notifier,
a Snowflake target, an eval runner. Each one wants the same four things, and
without a seam they each get bolted onto `new_project()` until the scaffolder is
the union of every feature anyone ever shipped.

A capability is that seam. It declares what it contributes:

    files      what to write into a project (templated, same `{{token}}` syntax)
    settings   permissions and plugins to merge into .claude/settings.json
    gate       path rules to merge into gate.yaml
    env        credentials it needs, so `pf doctor` can tell you what is missing

and nothing else. Adding a capability is one entry in `CAPABILITIES`; it does not
touch the scaffolder, the CLI, or the gate. Removing one is deleting that entry.

Capabilities are **declarative on purpose**. A capability that could run
arbitrary code at scaffold time would be a plugin system, and a plugin system
inside the thing that enforces the safety gate is a way around the safety gate.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pf.features import Feature
from pf.runtime.targets import WAREHOUSES, ProductionWarehouse
from pf.scaffold.generator import PROJECT_TARGETS, render, render_profiles


@dataclass(frozen=True)
class Capability:
    """One optional feature a project can be scaffolded with."""

    name: str
    description: str
    files: dict[str, str] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)
    gate: dict[str, list[str]] = field(default_factory=dict)
    env: tuple[str, ...] = ()
    # CI jobs, keyed by job id, merged into the project's one master workflow by
    # `pf.scaffold.ci`. A capability contributes a job, not a workflow file:
    # sixteen files each re-deciding "did this PR touch my project" is how a
    # project's CI stopped being readable in one place. Each block guards itself
    # on `needs.changes.outputs.<area>` — see `pf.scaffold.ci.CHANGE_AREAS`.
    ci_jobs: dict[str, str] = field(default_factory=dict)
    # Capabilities that must be applied first. Kept explicit so ordering is a
    # declared fact rather than dict-insertion luck.
    requires: tuple[str, ...] = ()
    # Applied to a new project without being asked for, and backfilled into
    # existing ones by `pf bootstrap`. The mirror of `Tool.default_enabled`, and
    # for the same reason: an opt-in capability reaches only the projects whose
    # author remembered the flag, which is how one project ended up with a CI
    # merge gate and seven did not. Opt out with `pf new-project --without`.
    #
    # A new project gets the whole default set, because none of its files exist
    # yet and nothing can be overwritten. Backfilling an existing project is
    # narrower on purpose — see `pf.scaffold.bootstrap._bootstrap_capabilities`,
    # which refuses to apply a capability whose files are only partly present
    # rather than rewriting one someone has edited.
    default_enabled: bool = False
    # What this capability adds to a project's architecture map, when the
    # derivation from `files` would not say it well. Optional, and usually
    # absent: `pf.features.derive` reads `files` and contributes a row only for
    # territory no existing feature claims, which is the case that would
    # otherwise surface as an unmapped directory. Declare one to give it a real
    # title, a lane, or a `count_kind`.
    feature: Feature | None = None
    # Only offered to an import whose source actually targets this warehouse.
    # Without it, `pf onboard` wires in every registered capability, and a
    # Postgres project would be handed a Snowflake production target it has no
    # use for and no credentials to fill. Declared here rather than special-cased
    # in the onboarder so a `bigquery` sibling is one more entry.
    warehouse: str = ""


# --------------------------------------------------------------- github -----
IMPACT_JOB = """\
  # The merge gate, in CI. Runs the same `pf impact-gate` the developer's
  # pre-commit hook runs, so a change that bypassed the local hook (--no-verify,
  # a web edit, a bot commit) still cannot merge without its blast radius being
  # reported.
  impact-gate:
    needs: changes
    if: needs.changes.outputs.models == 'true' || needs.changes.outputs.sources == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # impact needs the merge base, not a shallow clone
      - uses: astral-sh/setup-uv@v5
      - run: uv sync

      - name: Models this PR touches
        id: changed
        run: |
          CHANGED=$(git diff --name-only origin/${{ github.base_ref }}...HEAD \\
            -- 'groups/{{group}}/projects/{{project}}/transform/models/**/*.sql' \\
            | xargs -r -n1 basename | sed 's/\\.sql$//' | sed 's/^/model:/' | paste -sd, -)
          [ -z "$CHANGED" ] && echo "no model changes"
          echo "models=$CHANGED" >> "$GITHUB_OUTPUT"

      # Gate against the *base*, not the branch. The question a merge gate
      # answers is "what does this break in {{group}}/{{project}} as it stands",
      # and only the base graph can answer it:
      #
      #   a model this PR adds is not in the base graph, so it has no blast
      #     radius and does not block — gated against the branch instead, every
      #     new model blocks on the new models added beside it, which makes the
      #     gate unusable for exactly the changes that need reviewing most
      #   a model this PR deletes still is in the base graph, so its consumers
      #     are found — gated against the branch it resolves to nothing and the
      #     most dangerous change there is passes silently
      #
      # `pf kg build` parses the dbt project first. Without a manifest the graph
      # holds no models, every blast-radius query comes back empty, and the gate
      # passes because it found nothing rather than because there is nothing.
      - name: Blast radius against the base
        if: steps.changed.outputs.models != \'\'
        run: |
          git checkout --detach origin/${{ github.base_ref }}
          if [ ! -f "groups/{{group}}/projects/{{project}}/transform/dbt_project.yml" ]; then
            echo "{{group}}/{{project}} does not exist on ${{ github.base_ref }} yet — nothing there to break"
            exit 0
          fi
          uv run pf kg build {{group}} {{project}}
          uv run pf impact-gate {{group}} {{project}} "${{ steps.changed.outputs.models }}"
"""

GITHUB_README = """\
# GitHub integration — {{group}}/{{project}}

`pf impact-gate` runs on every PR that touches this project's models or sources.
A change with a breaking blast radius fails the check and names the exposure
owners who need to know.

## What it does not do
It does not open PRs, comment on them, or read repository contents beyond the
diff. Those need a token; this needs none, because it runs inside the repo's own
CI. Add write-scoped automation as a separate capability rather than widening
this one — the whole point of the gate is that it cannot be talked out of a
verdict by the thing it is gating.
"""

EVIDENCE_README = """\
# Reporting — Evidence BI

BI-as-code for **{{group}}/{{project}}**. Generated by `pf report build`, never
hand-maintained.

    dbt marts -> MetricFlow metrics -> MDL -> queries/metrics/*.sql -> pages/*.md

## The one rule

**Pages never restate business logic.** Every number traces to a metric compiled
into `queries/metrics/`. If a dashboard needs a figure that does not exist, the
fix is a metric definition in `transform/models/semantic/`, then `pf report build`
— not SQL in a page. Two pages filtering differently is how one company ends up
with two revenues.

## Ratio metrics

Ratio queries carry their numerator and denominator so a page re-divides at its
own grain: `sum(num) / sum(den)`. **Never `avg(ratio)`** — it is wrong at every
grain except the one it was computed at, and it is the most common BI bug there is.

## Commands

```bash
pf report build {{group}} {{project}}    # regenerate from the semantic layer
pf report audit {{group}} {{project}}    # mechanical quality score
cd reporting && npm install && npm run sources && npm run dev
```

### Node version

Use **Node 20** (`.nvmrc` is committed). Evidence 40 does not build on Node 24 /
npm 11 — verified by building a pristine `evidence-dev/template`, which fails the
same way, so this is Evidence's supported-runtime boundary rather than anything
about this project. `npm run sources` and `npm run dev` work on newer Node;
`npm run build` needs 20.

## What is generated vs yours

| Generated — do not edit | Yours |
|---|---|
| `queries/metrics/*.sql` | extra pages you write by hand |
| `pages/index.md`, `pages/metrics/*.md` | `components/` |
| `sources/*/`, `evidence.config.yaml` | narrative text in generated pages* |

*Regenerating overwrites generated pages. Put durable narrative in a page you
own, or in the metric `description` so it survives.
"""


EVIDENCE_GITIGNORE = """\
.evidence/
build/
node_modules/
static/data/
"""


# ------------------------------------------------------------ warehouses ----
#: The generated README, shared by every production warehouse.
#:
#: One skeleton rather than one file per engine. The parts that vary — the
#: engine's name, its credentials, how it authenticates, what it does
#: differently from DuckDB — are filled from the `ProductionWarehouse` entry;
#: everything else is the same sentence in every project, which is the point.
#: Five hand-written copies of "development stays on DuckDB" is five chances for
#: the one nobody is reading to be wrong.
WAREHOUSE_README = """\
# Production warehouse — {{warehouse_title}}

**{{group}}/{{project}}** develops on DuckDB and runs production on
{{warehouse_title}}. One set of models serves both: the `sf_*` macros in
`platform/toolkits/dbt-snowflake` dispatch per adapter, so a model is written
once and compiles to whatever the *target* understands. `pf dialect` lists what
is covered, and `pf align validate {{group}} {{project}} --stage dialect` is the
gate that says whether this project is actually portable or merely untested.

Declaring this target does not make the models run on {{warehouse_title}}. That
gate passing is what does.

## Why development stays on DuckDB

A developer who needs a warehouse account to run the project stops running the
project. Every target but `prod` is a local DuckDB file, so `dbt build` works on
a laptop, offline, with no credentials, in seconds — and `base` exists so Recce
has a second state to diff against.

Only `prod` points at {{warehouse_title}}. Nothing in this capability can move
`dev`, `ci` or `base`, by construction.

## Credentials

Read from the environment at run time and **never written to a file here** —
`transform/profiles.yml` holds `env_var` calls, not values, because it is
committed:

{{env_block}}

{{auth_note}}

`pf doctor` reports which are missing. Never paste one into a chat, a model
file, or this repository.

## Running against it

The adapter is an optional extra — nothing on a laptop needs it, because every
target but `prod` is DuckDB and dbt only loads the adapter the selected target
names.

```bash
uv sync --extra {{warehouse_extra}}    # installs {{warehouse_adapter}}
DBT_TARGET=prod dbt build          # explicit, every time
pf align validate {{group}} {{project}} --stage dialect
```

There is deliberately no shortcut. The target is named on every invocation
because the failure mode — believing you are on dev and being on prod — is worse
than the typing.

{{caveats}}

## Switching

```bash
pf capability-add <warehouse> {{group}} {{project}}
```

`prod` is replaced in place; the DuckDB targets beside it, and anything you
hand-added to them, are left alone.
"""


def _env_block(wh: ProductionWarehouse) -> str:
    """Required credentials first, then the ones with defaults.

    Split because the distinction is the whole question an operator has when
    they read this: "what do I have to go and get" versus "what can I leave".
    Derived from the target rather than restated — a two-argument `env_var` has
    a default and is therefore optional, so the two lists cannot disagree with
    the profile they document.
    """
    referenced: list[str] = []
    optional: list[str] = []
    for value in wh.output.values():
        m = re.search(r"env_var\(\s*'([^']+)'(\s*,)?", str(value))
        if not m:
            continue
        (optional if m.group(2) else referenced).append(m.group(1))
    lines = ["    required:  " + ("  ".join(sorted(set(referenced))) or "—")]
    if optional:
        lines.append("    optional:  " + "  ".join(sorted(set(optional))))
    return "\n".join(lines)


def _caveats(wh: ProductionWarehouse) -> str:
    if not wh.caveats:
        return ""
    return "## What differs from DuckDB\n\n" + "\n".join(f"- {c}" for c in wh.caveats)


def warehouse_capability(wh: ProductionWarehouse) -> Capability:
    """Everything a production warehouse contributes, built from its declaration.

    The profile is `render_profiles` over the standard targets with **only**
    `prod` swapped, so enabling one strictly retargets production rather than
    replacing anyone's dbt config. Nothing reads `prod` until `DBT_TARGET`
    selects it, so a project carries it un-credentialed and inert.
    """
    docs = (WAREHOUSE_README
            .replace("{{warehouse_title}}", wh.title)
            .replace("{{warehouse_extra}}", wh.name)
            .replace("{{warehouse_adapter}}", wh.adapter)
            .replace("{{env_block}}", _env_block(wh))
            .replace("{{auth_note}}", wh.auth_note)
            .replace("{{caveats}}", _caveats(wh)))
    return Capability(
        name=wh.name,
        description=f"Run production on {wh.title} while development stays on DuckDB.",
        files={
            "transform/profiles.yml": render_profiles(
                "{{module}}", {**PROJECT_TARGETS, "prod": wh.output}),
            f"docs/{wh.name}.md": docs,
        },
        settings={
            "permissions": {"allow": ["Bash(pf align:*)", "Bash(pf dialect:*)"]},
            **({"enabledPlugins": list(wh.plugins)} if wh.plugins else {}),
        },
        env=wh.env,
        warehouse=wh.name,
        default_enabled=wh.default_enabled,
    )


ARCH_JOB = """\
  # Is the project's architecture map still true of the project?
  #
  # The map is generated and committed, so a PR that adds an exposure or drops a
  # metric should carry the map change beside it. Without this the file is
  # correct only until somebody forgets, and a stale map is worse than none: it
  # is read as current.
  #
  # `pf kg build` first, and not optionally. Counts come from the annotations
  # and the dbt manifest, so without a parse the graph holds no models, every
  # count reads zero and the check reports drift that is really a missing build.
  architecture:
    needs: changes
    if: needs.changes.outputs.any == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync

      - name: Build the graph this map is generated from
        run: uv run pf kg build {{group}} {{project}}

      # Fails on two things: a map that no longer matches its project, and a
      # directory no `Feature` claims. The second is a platform-side gap — a
      # capability or tool that writes somewhere the registry does not know
      # about — and it is reported here because here is where the platform is
      # what changed.
      - name: Architecture map is current
        run: uv run pf arch {{group}} {{project}} --check
"""

CAPABILITIES: dict[str, Capability] = {
    "evidence": Capability(
        name="evidence",
        description="Evidence BI reporting layer, generated from the semantic layer.",
        files={
            "reporting/README.md": EVIDENCE_README,
            "reporting/.gitignore": EVIDENCE_GITIGNORE,
        },
        settings={
            "permissions": {"allow": [
                "Bash(pf report:*)",
                "Bash(npm run dev:*)", "Bash(npm run build:*)",
                "Bash(npm run sources:*)",
            ]},
            "enabledPlugins": ["evidence-bi@platform"],
        },
        gate={
            # Generated artefacts and build output. Editing a compiled metric
            # query is how a page silently stops matching its metric definition.
            "denylist": [
                "**/reporting/queries/metrics/**",
                "**/reporting/.evidence/**",
                "**/reporting/build/**",
                "**/reporting/node_modules/**",
            ],
            "impact_required": ["**/reporting/pages/**"],
        },
        default_enabled=True,
    ),
    "github": Capability(
        name="github",
        description="Run the impact gate on every pull request touching this project.",
        files={"docs/github.md": GITHUB_README},
        ci_jobs={"impact-gate": IMPACT_JOB, "architecture": ARCH_JOB},
        settings={
            "permissions": {"allow": ["Bash(gh pr view:*)", "Bash(gh pr diff:*)"]},
        },
        gate={
            # CI config is infrastructure: an agent editing the gate that judges
            # it is the same conflict of interest as editing gate.yaml.
            "denylist": ["**/.github/workflows/**"],
        },
        default_enabled=True,
    ),
}

# One capability per production warehouse, generated from `pf.runtime.targets`.
# Registered here rather than written above because the whole point of the
# registry is that adding ClickHouse is an entry in a table, not a fifth
# near-identical block in this file that has to be kept in agreement with four
# others. `pf capabilities` and `pf new-project --with` see them exactly as if
# they had been written by hand.
CAPABILITIES.update({name: warehouse_capability(wh) for name, wh in WAREHOUSES.items()})



class UnknownCapability(KeyError):
    """Raised for a capability name that is not registered."""


def defaults() -> list[str]:
    """Capability names a project gets without asking.

    Read from the registry rather than hardcoded, for the same reason
    `_default_tools_yaml` asks the tool registry: registering the capability
    stays the only step. Tool-contributed capabilities are deliberately not
    included even when their tool is default-enabled — `tools.yaml` is where a
    tool's on/off decision lives, and the bootstrap `tools` step already applies
    them. Counting them here would apply the same capability twice, from two
    sources of truth that can disagree.
    """
    return sorted(n for n, c in CAPABILITIES.items() if c.default_enabled)


def resolve(names: list[str]) -> list[Capability]:
    """Resolve names to capabilities, dependencies first, each applied once."""
    out: list[Capability] = []
    seen: set[str] = set()

    def visit(name: str, chain: tuple[str, ...] = ()) -> None:
        if name in seen:
            return
        if name in chain:
            raise ValueError(f"capability cycle: {' -> '.join((*chain, name))}")
        if name not in CAPABILITIES:
            raise UnknownCapability(
                f"unknown capability '{name}'. Available: "
                f"{', '.join(sorted(CAPABILITIES)) or '(none)'}")
        cap = CAPABILITIES[name]
        for dep in cap.requires:
            visit(dep, (*chain, name))
        seen.add(name)
        out.append(cap)

    for n in names:
        visit(n)
    return out


def apply(cap: Capability, root: Path, project_dir: Path,
          ctx: dict[str, Any]) -> list[Path]:
    """Write one capability's files and merge its settings. Returns what changed.

    Files are written relative to the *project*, except `.github/**`, which
    belongs to the repository — a workflow only runs from the repo root.
    """
    written: list[Path] = []
    for rel, template in cap.files.items():
        rendered_rel = render(rel, ctx)
        base = root if rendered_rel.startswith(".github/") else project_dir
        target = base / rendered_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(template, ctx))
        written.append(target)

    if cap.settings:
        settings_path = project_dir / ".claude" / "settings.json"
        if settings_path.exists():
            settings = json.loads(settings_path.read_text())
            _merge(settings, cap.settings)
            settings_path.write_text(json.dumps(settings, indent=2) + "\n")
            written.append(settings_path)

    return written


def _merge(base: dict[str, Any], extra: dict[str, Any]) -> None:
    """Deep-merge, appending lists rather than replacing them.

    Replacing would let a capability silently drop a permission or plugin that
    another one added — the failure would show up much later as an agent that
    mysteriously cannot run a command.
    """
    for key, value in extra.items():
        if isinstance(value, dict):
            _merge(base.setdefault(key, {}), value)
        elif isinstance(value, list):
            current = base.setdefault(key, [])
            current.extend(v for v in value if v not in current)
        else:
            base[key] = value


def gate_additions(caps: list[Capability]) -> dict[str, list[str]]:
    """Union of the gate rules a set of capabilities contributes."""
    merged: dict[str, list[str]] = {}
    for cap in caps:
        for section, patterns in cap.gate.items():
            bucket = merged.setdefault(section, [])
            bucket.extend(p for p in patterns if p not in bucket)
    return merged


def missing_env(caps: list[Capability]) -> dict[str, list[str]]:
    """Credentials each capability declares that are not set. For `pf doctor`."""
    import os

    return {
        cap.name: [v for v in cap.env if not os.environ.get(v)]
        for cap in caps
        if any(not os.environ.get(v) for v in cap.env)
    }
