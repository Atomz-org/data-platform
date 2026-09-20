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
from pf.scaffold.claude_settings import normalize as normalize_settings
from pf.scaffold.generator import PROJECT_TARGETS, render, render_profiles


@dataclass(frozen=True)
class Capability:
    """One optional feature a project can be scaffolded with."""

    name: str
    description: str
    files: dict[str, str] = field(default_factory=dict)
    # Files that are *seeded*, not generated: written when absent, left alone
    # when present. `apply` otherwise rewrites every target wholesale, which is
    # correct for a generated artefact and destructive for one a human is
    # expected to edit — a policy overlay, a README, a profiles.yml. Without this
    # the only protection is `_bootstrap_capabilities` refusing a partial
    # backfill, and `pf capability-add` deliberately bypasses that.
    preserve: tuple[str, ...] = ()
    settings: dict[str, Any] = field(default_factory=dict)
    #: MCP servers this capability contributes, keyed by server name and merged
    #: into the project's `.mcp.json`. Merged rather than written like `files`,
    #: because `.mcp.json` is a file a project also edits by hand — a wholesale
    #: rewrite on `pf capability-add` would silently drop every server someone
    #: added beside this one. Declarative like the rest of a capability: a
    #: server definition, not a hook that runs one.
    mcp: dict[str, Any] = field(default_factory=dict)
    #: Obligations this capability introduces, in `policy.yaml`'s shape, written
    #: to the generated `policy.capabilities.yaml` beside the platform floor.
    #:
    #: A capability that adds machinery usually adds a rule about using it, and
    #: before this the rule had nowhere to live: it went into a skill as prose,
    #: which `pf semantic policy` cannot see and no gate can enforce. The whole
    #: point of the policy layer is that intent, constraint, artifact and evidence
    #: stay linked — a capability whose obligations are only documented breaks
    #: that chain at the first link.
    #:
    #: These layer through `merge_policies` like every other overlay, so a
    #: capability **may tighten the floor and may never relax it**. Declaring a
    #: policy with an inherited id and a lower severity raises `PolicyRelaxation`
    #: at load time rather than quietly widening what the platform allows.
    #:
    #: Be honest in `enforced_by`. An obligation with no check yet should name
    #: none — `pf semantic policy` reports it as unenforced, and an unenforced
    #: policy you can see beats an enforced-looking one that never runs.
    policies: tuple[dict[str, Any], ...] = ()
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

      # A breaking radius — a mart that feeds a metric or an exposure — needs a
      # decision record in the same change to pass. The gate still prints the
      # whole radius and names the owners; the decision is what the reviewer
      # reads instead of overriding a red job. `decisions/README.md` is the
      # scaffold's, not a decision.
      - name: Decisions this PR adds or changes
        id: decided
        run: |
          DECIDED=$(git diff --name-only origin/${{ github.base_ref }}...HEAD \\
            -- 'groups/{{group}}/projects/{{project}}/decisions/*.md' \\
            | grep -v '/README\\.md$' | paste -sd, -)
          echo "decisions=$DECIDED" >> "$GITHUB_OUTPUT"

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
          uv run pf impact-gate {{group}} {{project}} "${{ steps.changed.outputs.models }}" \\
            --decisions "${{ steps.decided.outputs.decisions }}"
"""

LOOPS_README = """\
# Loops — {{group}}/{{project}}

The platform's agents watch this project on a schedule. What they find goes to
`STATE.md`; what they *propose* becomes a pull request once the loop has earned
that right. Nothing here merges on its own.

```bash
pf loop list {{group}} {{project}}          # every loop, born vs earned level
pf loop run-all {{group}} {{project}}       # run them, refresh STATE.md
pf loop ladder {{group}} {{project}}        # what blocks the next rung
pf loop proposals list                      # what loops proposed; accept / reject
pf ask {{group}} {{project}} "revenue by month"   # governed metrics, no SQL
pf logs list {{group}} {{project}}          # every agent run, traced
```

## Memory — `decisions/loop-memory.yaml`

What this project has decided about its own findings. A suppression needs a
reason and should have an expiry; `pf loop memory audit` lists the ones that do
not. Reviewed in pull requests like any decision. Memory filters findings and
nothing else — it cannot name a file or loosen a budget.

## Trace logs — `logs/trace/`

Every loop run, every question and every proposal writes a JSONL transcript:
intent, what the agent understood, the request, the response, each tool call
and result, each deterministic step. `pf logs show <run-id>` renders one.
The directory is gitignored; the ledger (`loop-ledger.json`) is what is committed.

## Delivery

`--notify` posts to the group's channel — `groups/{{group}}/notify.yaml`, which
names an environment variable rather than holding the webhook URL.
"""

LOOP_MEMORY = """\
# Loop memory for {{group}}/{{project}} — decisions about recurring findings.
#
# An entry: pattern (glob, or /regex/), loop (or "*"), a REQUIRED note saying
# why, and ideally an expiry. `verb: annotate` keeps the finding and appends the
# note; the default `suppress` drops it. `pf loop memory add|list|forget|audit`.
#
# This file is reviewed in pull requests: a suppression is the statement
# "we will stop looking at this", and that belongs in a diff.
entries: []
"""

GITHUB_README = """\
# GitHub integration — {{group}}/{{project}}

`pf impact-gate` runs on every PR that touches this project's models or sources.
A radius that reaches a metric or an exposure blocks unless the same PR adds or
edits a decision record under `decisions/` — the report is still printed and
the owners still named; the decision is what a reviewer reads.
A change with a breaking blast radius fails the check and names the exposure
owners who need to know.

## What it does not do
It does not open PRs, comment on them, or read repository contents beyond the
diff. Those need a token; this needs none, because it runs inside the repo's own
CI. Add write-scoped automation as a separate capability rather than widening
this one — the whole point of the gate is that it cannot be talked out of a
verdict by the thing it is gating.
"""

# The Evidence reporting capability lives with its tool: `pf.tools.evidence`.
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
    docs = (
        WAREHOUSE_README.replace("{{warehouse_title}}", wh.title)
        .replace("{{warehouse_extra}}", wh.name)
        .replace("{{warehouse_adapter}}", wh.adapter)
        .replace("{{env_block}}", _env_block(wh))
        .replace("{{auth_note}}", wh.auth_note)
        .replace("{{caveats}}", _caveats(wh))
    )
    return Capability(
        name=wh.name,
        description=f"Run production on {wh.title} while development stays on DuckDB.",
        files={
            "transform/profiles.yml": render_profiles("{{module}}", {**PROJECT_TARGETS, "prod": wh.output}),
            f"docs/{wh.name}.md": docs,
        },
        settings={
            "permissions": {"allow": ["Bash(pf align:*)", "Bash(pf dialect:*)"]},
            **({"enabledPlugins": dict.fromkeys(wh.plugins, True)} if wh.plugins else {}),
        },
        mcp=dict(wh.mcp),
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

# ------------------------------------------------------------------- air --
AIR_JOB = """\
  # The AI-control merge gate. Blocks only on controls this entity actually
  # committed to in its `air.yaml` baseline; everything else in the catalogue is
  # reported into the job summary and does not fail. The platform ships with
  # known gaps and says so, rather than hiding them behind a green check.
  #
  # The vendored control catalogue (`vendor/ai-governance-framework`) is
  # load-bearing and unique to this job: without it every control assesses as
  # `unexercised` and the gate passes for the wrong reason.
  #
  # It is initialised **by name** rather than with `submodules: true`, which
  # asks for all of them. One unreachable pin anywhere under `vendor/` would
  # otherwise take this gate down with it — and that is not hypothetical: the
  # `asqav-compliance` upstream was deleted and every `submodules: true`
  # checkout in this repository failed at step one for two days. A governance
  # check that cannot start is indistinguishable from one that passed.
  air-baseline:
    needs: changes
    if: needs.changes.outputs.any == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Vendored control catalogue
        run: git submodule update --init vendor/ai-governance-framework
      - uses: astral-sh/setup-uv@v5
      - run: uv sync

      - name: Verify the vendored catalogue
        run: uv run pf air verify

      - name: Control coverage
        run: uv run pf air coverage {{group}} {{project}} --markdown >> "$GITHUB_STEP_SUMMARY"

      # The blocking step. Exits non-zero when a committed control is failing.
      - name: Committed baseline
        run: uv run pf air gate {{group}} {{project}}
"""

AIR_DOCS = """\
# AI risk controls — {{project}}

This project declares which AI controls it commits to in `air.yaml`, and
`pf air gate {{group}} {{project}}` blocks the merge when one of them is not
enforced. Controls come from whichever catalogues are registered —
`pf air catalogues` lists them and where each is checked out.

| command | what it answers |
| --- | --- |
| `pf air catalogues` | which control catalogues are registered |
| `pf air controls` | which controls exist |
| `pf air show <id>` | one control, and every regulation it discharges |
| `pf air baseline {{group}} {{project}} --suggest` | the controls that already pass |
| `pf air coverage {{group}} {{project}}` | which of them this project enforces |
| `pf air gaps` | only the ones it does not |
| `pf air crosswalk eu-ai-act` | the regulator's view of the same facts |
| `pf air register {{group}} {{project}}` | regenerate `governance/air-register.md` |

## Declaring a baseline

`air.yaml` is hand-written and carries the judgement:

- `baseline:` — controls this project commits to. These **block the merge**.
- `accepted:` — controls consciously not taken. `reason` and `owner` are both
  required, because an acceptance without them is a gap with better formatting.
- `profile:` — where this project sits in the framework's taxonomy.

A project may add to its group's baseline; it cannot remove from it. The way to
drop a control is `accepted:`, which leaves a name attached to the decision.

## The register is generated

`governance/air-register.md` is derived from `air.yaml` plus a fresh coverage
run and is on the gate denylist — hand-editing it would make it disagree with
the declaration it came from. Change `air.yaml`, then `pf air register`.

It carries the credit line of every catalogue it drew from, collected from the
sources actually loaded rather than templated — so a catalogue swapped out takes
its obligation with it, and one added brings its own.
"""

# The starter declaration. Deliberately empty of baseline entries: a scaffolder
# that pre-commits a project to four controls produces four commitments nobody
# made, and the first `pf air gate` would fail on a decision never taken.
#
# Lives here with the other capability file templates rather than in `pf.air`,
# which keeps `pf.capabilities` free of any import into `pf.air` — `pf.tools.spec`
# imports this module, and `pf.air.register` reads `pf.tools.config`.
AIR_CONFIG = """\
# Which AI controls {{project}} commits to.
#
# Read, not generated — `governance/air-register.md` is the generated half.
# Control ids come from whichever catalogues are registered: `pf air catalogues`
# lists them, `pf air controls` lists the ids, `pf air show <id>` explains one.
#
# Merged over the group's air.yaml. `baseline` is a union with the group's, not
# a replacement: an entity may commit to more than its family, never to less.
version: 1

# Where this project sits in its catalogue's taxonomy, if it declares one.
# Free-form until then.
#
# profile:
#   ai_type: Agentic_AI
#   architecture_pattern: Agentic/Autonomous_AI
profile: {}

# Controls this project commits to. `pf air gate` blocks the merge when one of
# these is failing; everything else is reported and advisory.
#
# Start from `pf air baseline {{group}} {{project}} --suggest`, which proposes
# only what already passes — a ratchet against regression rather than a wall of
# work nobody agreed to. Accepting the proposal stays a person's act.
baseline: []

# Controls consciously not taken. `reason` and `owner` are both required: an
# acceptance without a reason is a gap with better formatting, and one without
# an owner is a decision nobody can be asked about.
#
# accepted:
#   - control: <id>
#     reason: >
#       Why this project does not take it, in a sentence somebody can disagree with.
#     owner: someone@example.com
#     review_by: 2027-01-01
accepted: []
"""


# ----------------------------------------------------------- governance -----
# Seeded inert. Every policy below is commented out, so scaffolding a project or
# backfilling this capability into eight existing ones changes no verdict
# anywhere — the file exists to be found and edited, not to take effect on
# arrival. A capability that silently tightened the gate on adoption would be
# discovered as a broken build in a project nobody had touched.
GOVERNANCE_POLICY = """\
# Policy overlay for {{group}}/{{project}}.
#
# The platform ships a policy floor in `platform/src/pf/ontology/policy.yaml`
# that applies to every project. This file layers over it, and over any group
# overlay at `groups/{{group}}/ontology/policy.yaml`, for the obligations that
# are this entity's alone — a jurisdiction, a customer contract, a retention
# rule a sister does not share.
#
# Vocabulary is deliberately NOT layered here. Two sisters must mean the same
# thing by `Payment` or a roll-up adds two numbers that merely share a name;
# concepts live in the group ontology for that reason. What must *hold* is the
# part that is genuinely local, so it is the part that layers.
#
# THIS FILE MAY ONLY TIGHTEN.
#
#   add       declare a policy the platform does not have
#   tighten   raise an inherited policy's severity (info -> warning -> error)
#   enforce   name another artifact or evidence kind for an inherited policy
#
# Lowering a severity raises `PolicyRelaxation` at load time, and there is no
# syntax for deleting an inherited policy. An omitted `severity:` means inherit,
# so adding an `enforced_by` line cannot silently escalate the rule.
#
# Inspect the resolved result — including which layer set each severity — with:
#
#     pf semantic policy {{group}} {{project}}

policies: []

# --- examples, all inert until uncommented -----------------------------------
#
# Tighten an inherited policy. `mart-declares-grain` ships as a warning; here an
# undeclared grain would block the merge.
#
# policies:
#   - id: mart-declares-grain
#     severity: error
#
# Declare an obligation the platform does not know about. Note it names no
# `enforced_by`: `pf semantic policy` will report it as unenforced, which is the
# honest state until the check exists. Claiming enforcement that does not exist
# is worse than declaring none — it ends the conversation.
#
#   - id: retention-window-declared
#     intent: >
#       A table holding personal data must declare how long it keeps it, or the
#       retention promise is prose nobody can verify.
#     applies_to: {role_glob: "pii_*"}
#     constraint: retention_declared
#     severity: error
#
# Add enforcement to an inherited policy without claiming ownership of it. The
# severity's owner stays where it was; only the artifact list grows.
#
#   - id: pii-not-in-consumption
#     enforced_by: [pf.local.checks:pii_sweep]
#     evidence: [pf loop run pii-audit]
"""


KG_CURRENT_JOB = """\
  # The graph has no clock. One built before a model landed answers every query
  # confidently and wrongly, and nothing else notices — it simply holds fewer
  # nodes than the project has models. Every other job here trusts that graph:
  # the impact gate computes a blast radius from it, and an agent reads its
  # context card. A stale graph makes both of those quietly wrong rather than
  # loudly broken, which is why this is a gate and not a reminder.
  kg-current:
    needs: changes
    if: needs.changes.outputs.any == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync

      # `pf kg check` parses the dbt project first — `target/` is gitignored, so
      # a runner has no manifest to compare the committed graph against, and
      # without one the check reports "not exercised" and passes.
      #
      # It compares only what a runner without a warehouse can see: models,
      # metrics and exposures come from the dbt manifests, which this checkout
      # has. Columns are backfilled from information_schema, which it does not —
      # comparing those too would be red on every pull request forever.
      - name: Is the committed graph current?
        run: uv run pf kg check {{group}} {{project}} --strict
"""


CAPABILITIES: dict[str, Capability] = {
    "air": Capability(
        name="air",
        description="AI control baseline: declare it in air.yaml, gate the merge on it.",
        files={
            "air.yaml": AIR_CONFIG,
            "docs/air.md": AIR_DOCS,
        },
        ci_jobs={"air-baseline": AIR_JOB},
        settings={
            "permissions": {
                "allow": [
                    "Bash(pf air:*)",
                ]
            },
        },
        gate={
            # Generated from air.yaml on every run. Hand-editing it makes the
            # register disagree with the declaration it was derived from, and the
            # next `pf air register` discards the edit — the same argument that
            # denies every other generated artefact here.
            "denylist": ["**/governance/air-register.md"],
            # Changing what an entity commits to is a governance decision, not a
            # refactor. It stays editable — the register is the generated half —
            # but the blast radius gets reported first.
            "impact_required": ["**/air.yaml"],
        },
        default_enabled=True,
    ),
    "governance": Capability(
        name="governance",
        description="Project-scoped policy overlay, layered over the platform and group floors. Tightening only.",
        files={"governance/policy.yaml": GOVERNANCE_POLICY},
        # Seeded, never regenerated: this is the one file in the capability a
        # project is expected to own. Re-applying must not overwrite it.
        preserve=("governance/policy.yaml",),
        # A policy overlay decides whether a change is allowed to land, so it is
        # not something a change may quietly relax on its way past. Edits are
        # visible rather than blocked — the loosening guard lives in the loader,
        # where it can read what the edit actually did.
        gate={"impact_required": ["**/governance/policy.yaml"]},
        # The obligations this platform states in prose and enforces in config,
        # written down where `pf semantic policy` can see them. Each one already
        # had a mechanism; none had an entry in the chain, so "is the isolation
        # rule actually enforced?" had no answer but a grep.
        policies=(
            {
                "id": "entity-isolation-enforced",
                "intent": (
                    "Business logic does not transfer between entities. A session "
                    "that can read a sister project will carry an assumption across "
                    "— a grain, a status enum, a revenue definition — and the bug "
                    "that results is invisible, because the code it came from is "
                    "correct in the project it came from."
                ),
                "applies_to": {"artifact_glob": "**/groups/*/projects/*/**"},
                "constraint": "path_denied",
                "params": {"denies": "sibling and cross-group reads"},
                "severity": "error",
                "enforced_by": [
                    "pf.scaffold.generator:PROJECT_SETTINGS",
                    "platform/hooks/pre_tool_use.py",
                ],
                "evidence": ["pf gate"],
            },
            {
                "id": "vendor-is-read-only",
                "intent": (
                    "A vendored upstream is evidence of what an external project "
                    "actually does. Editing one turns it into a fork wearing a "
                    "submodule's name, and every later diff against upstream reads "
                    "as drift that nobody introduced."
                ),
                "applies_to": {"artifact_glob": "vendor/**"},
                "constraint": "path_denied",
                "severity": "error",
                "enforced_by": ["gate.yaml:denylist", "platform/hooks/pre_tool_use.py"],
                "evidence": ["pf gate", "pf vendor drift"],
            },
            {
                "id": "agent-settings-schema-valid",
                "intent": (
                    "A settings file the client rejects loads none of the plugins it "
                    "declares, and says so nowhere a session can see. The platform's "
                    "own retrieval tools arrive as plugins, so a schema error "
                    "silently removes kg_search and impact_analysis — and an agent "
                    "with no graph reads files instead and never reports why."
                ),
                "applies_to": {"artifact_glob": "**/.claude/settings.json"},
                "constraint": "schema_current",
                "severity": "error",
                "enforced_by": ["pf.scaffold.claude_settings:normalize"],
                "evidence": ["pf bootstrap"],
            },
        ),
        default_enabled=True,
    ),
    "loops": Capability(
        name="loops",
        description="Loop memory, proposal review, trace logs and the metric-question "
        "surface — the agentic layer, reaching every project.",
        files={
            "docs/loops.md": LOOPS_README,
            "decisions/loop-memory.yaml": LOOP_MEMORY,
        },
        settings={
            "permissions": {
                "allow": [
                    "Bash(pf loop:*)",
                    "Bash(pf ask:*)",
                    "Bash(pf logs:*)",
                    "Bash(pf align:*)",
                    "Bash(pf evals-gate:*)",
                ]
            },
        },
        gate={
            # Proposals and trace logs are generated, untracked artefacts.
            # The ledger and levels files are deliberately NOT here even
            # though hand-editing them would forge a track record: they are
            # *committed* records — promotion evidence has to travel with the
            # repo — and this gate's denylist means "generated, never
            # tracked" (`tracked_denied` enforces exactly that). Their
            # protection is the same as the governance store's: append-only
            # writers, and review of the diff.
            "denylist": [
                "data/proposals/**",
                "**/logs/trace/**",
            ],
        },
        default_enabled=True,
    ),
    "data-quality": Capability(
        name="data-quality",
        description="Data-quality obligations served by the dbt-expectations and dbt-elementary toolkits.",
        # No files. The toolkits ship the skills, `DEFAULT_TOOLKITS` enables them,
        # and what this capability adds is the part neither of those can hold: the
        # obligations they exist to serve. A skill can say "bound a money column";
        # only a policy can be asked whether anything checks that it happened.
        policies=(
            {
                "id": "money-amount-bounded",
                "intent": (
                    "A monetary column with no lower bound accepts the negative "
                    "row that a refund, a sign flip or a bad join produces, and it "
                    "reaches a metric as a quietly smaller number. The currency "
                    "rule makes the amount interpretable; this makes it credible."
                ),
                "applies_to": {"role": "money_amount"},
                "constraint": "range_asserted",
                "params": {"suggested": "dbt_expectations.expect_column_values_to_be_between"},
                "severity": "warning",
                # Deliberately unenforced: no check reads a model's tests yet.
                # `pf semantic policy` reports this as unenforced, which is the
                # honest state and the reason it is worth declaring now.
                "enforced_by": [],
                "evidence": ["dbt test"],
            },
            {
                "id": "source-declares-freshness",
                "intent": (
                    "A mart is stale because its source was. Monitoring the mart "
                    "names the wrong artefact to go fix, and monitoring nothing "
                    "means the first report of a stopped pipeline comes from "
                    "whoever opened the dashboard."
                ),
                "applies_to": {"artifact_glob": "**/transform/models/**/_*__sources.yml"},
                "constraint": "freshness_declared",
                "severity": "warning",
                "enforced_by": [],
                "evidence": ["dbt source freshness", "dbt test"],
            },
            {
                "id": "anomaly-tests-do-not-gate-merge",
                "intent": (
                    "An anomaly test judges data; a merge gate judges code. Wiring "
                    "a statistical test into the gate blocks a correct change "
                    "because yesterday's load was small, and the cure is always to "
                    "weaken the test — which is how the monitoring stops working."
                ),
                "applies_to": {"artifact_glob": "**/.github/workflows/**"},
                "constraint": "not_in_gate",
                "params": {"excludes": "elementary anomaly tests"},
                "severity": "error",
                "enforced_by": ["pf.capabilities:IMPACT_JOB"],
                "evidence": ["pf impact-gate"],
            },
        ),
        default_enabled=True,
    ),
    "github": Capability(
        name="github",
        description="Run the impact gate and the graph currency check on every pull request touching this project.",
        files={"docs/github.md": GITHUB_README},
        ci_jobs={"impact-gate": IMPACT_JOB, "kg-current": KG_CURRENT_JOB, "architecture": ARCH_JOB},
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
                f"unknown capability '{name}'. Available: {', '.join(sorted(CAPABILITIES)) or '(none)'}"
            )
        cap = CAPABILITIES[name]
        for dep in cap.requires:
            visit(dep, (*chain, name))
        seen.add(name)
        out.append(cap)

    for n in names:
        visit(n)
    return out


def apply(cap: Capability, root: Path, project_dir: Path, ctx: dict[str, Any]) -> list[Path]:
    """Write one capability's files and merge its settings. Returns what changed.

    Files are written relative to the *project*, except `.github/**`, which
    belongs to the repository — a workflow only runs from the repo root.
    """
    written: list[Path] = []
    for rel, template in cap.files.items():
        rendered_rel = render(rel, ctx)
        base = root if rendered_rel.startswith(".github/") else project_dir
        target = base / rendered_rel
        # A seeded file is written once. Re-applying the capability — which
        # `pf capability-add` does on demand, past the backfill's own guard —
        # must not overwrite what the project has since written in it.
        if rel in cap.preserve and target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(template, ctx), encoding="utf-8")
        written.append(target)

    if cap.settings:
        settings_path = project_dir / ".claude" / "settings.json"
        if settings_path.exists():
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            # Bring the file to the current schema *before* merging into it. A
            # capability contributes `enabledPlugins` as a record now, and
            # merging a record into a project still holding the legacy list
            # would hand `_merge` a list where it expects a dict — turning "this
            # project is one schema version behind" into a bootstrap crash
            # instead of the repair it should be.
            normalize_settings(settings)
            if isinstance(settings.get("enabledPlugins"), list):
                # Legacy scaffold form; Claude Code expects a record.
                settings["enabledPlugins"] = dict.fromkeys(settings["enabledPlugins"], True)
            _merge(settings, cap.settings)
            settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
            written.append(settings_path)

    if cap.mcp:
        mcp_path = project_dir / ".mcp.json"
        # Unlike settings.json this file is created when absent: a project has
        # `.claude/settings.json` from the scaffolder, but `.mcp.json` exists
        # only once something needs it, and a warehouse capability is exactly
        # such a something.
        config = json.loads(mcp_path.read_text()) if mcp_path.exists() else {}
        _merge(config, {"mcpServers": cap.mcp})
        mcp_path.write_text(json.dumps(config, indent=2) + "\n")
        written.append(mcp_path)

    return written


def _merge(base: dict[str, Any], extra: dict[str, Any]) -> None:
    """Deep-merge, appending lists rather than replacing them.

    Replacing would let a capability silently drop a permission or plugin that
    another one added — the failure would show up much later as an agent that
    mysteriously cannot run a command.
    """
    for key, value in extra.items():
        if isinstance(value, dict):
            current = base.setdefault(key, {})
            if not isinstance(current, dict):
                # A capability contributing a record into a key this project
                # holds as something else. `pf.scaffold.claude_settings.normalize`
                # migrates the shapes we know shipped wrong; whatever is left
                # here is a real disagreement, and merging past it would quietly
                # drop one side. Name the key — an AttributeError raised deep in
                # a recursive merge says nothing about which setting is at fault.
                raise TypeError(
                    f"settings key {key!r} is {type(current).__name__}, expected "
                    f"an object — `pf bootstrap` migrates the known legacy shapes"
                )
            _merge(current, value)
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


def policy_additions(caps: list[Capability]) -> list[dict[str, Any]]:
    """Every policy a set of capabilities declares, first declaration winning.

    Deduplicated by id so two capabilities naming the same obligation produce one
    entry rather than a file that fails its own layering check. Order follows the
    capability order, which `resolve` has already made deterministic — a generated
    file that reshuffles itself between runs is a diff nobody can read.
    """
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for cap in caps:
        for policy in cap.policies:
            pid = policy.get("id")
            if pid in seen:
                continue
            seen.add(pid)
            out.append({**policy, "_capability": cap.name})
    return out


#: Where capability-declared policies are written. Beside the platform floor
#: rather than at the repo root, because that is the layer they belong to: a
#: capability is a platform feature, so its obligations are platform-scope and
#: layer over `policy.yaml` exactly as a group's layer over the platform's.
CAPABILITY_POLICY_FILE = "policy.capabilities.yaml"

POLICY_HEADER = """\
# GENERATED from `Capability.policies` — do not edit.
#
# Written by `pf bootstrap` (step: capability policies) and by `pf new-project`.
# Layered over policy.yaml at load time by `pf.ontology.model.load_ontology`,
# through the same `merge_policies` guard every other overlay goes through: a
# capability may tighten the floor and may never relax it.
#
# To change a rule here, change the `policies=` on the capability that declares
# it — the `_capability` key on each entry names which one.
"""


def write_capability_policies(root: Path, caps: list[Capability] | None = None) -> Path:
    """Regenerate the capability policy overlay. Returns the path written.

    Defaults to every default-enabled capability, which is what makes this
    idempotent and safe to run on every bootstrap: the file is a pure function of
    the registry, so a capability removed from the registry disappears from the
    overlay rather than lingering as a rule nothing declares any more.
    """
    import yaml

    caps = resolve(defaults()) if caps is None else caps
    policies = policy_additions(caps)
    path = Path(root) / "platform" / "src" / "pf" / "ontology" / CAPABILITY_POLICY_FILE
    body = yaml.safe_dump({"policies": policies}, sort_keys=False, width=88)
    path.write_text(POLICY_HEADER + body)
    return path


def missing_env(caps: list[Capability]) -> dict[str, list[str]]:
    """Credentials each capability declares that are not set. For `pf doctor`."""
    import os

    return {
        cap.name: [v for v in cap.env if not os.environ.get(v)]
        for cap in caps
        if any(not os.environ.get(v) for v in cap.env)
    }
