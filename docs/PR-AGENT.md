# PR-Agent — adoption plan

Status: proposal. Pin lands in PR #330 (`vendor/pr-agent`, MIT, role `reference`).
Nothing below is built yet. This document says what we would take, where it
attaches, and what must be true before each phase ships.

## 1. What we are actually adopting

`vendor/pr-agent` is the community fork of PR-Agent (v0.45.0). Read the survey
before assuming a feature exists — three things people expect are **not** in
this tree:

| expected | reality |
|---|---|
| `/compliance` with `pr_compliance_checklist.yaml` | Hosted Qodo only. The two root files in the vendored repo are read by zero lines of `pr_agent/`. |
| `best_practices.md` auto-loading | Qodo only. OSS route is `config.repo_context_files`. |
| per-folder configuration (`allow_only_specific_folders`) | Implemented for Bitbucket Server only. Config is repo-global; scoping is one invocation per scope. |

What *is* there, and what we would use:

- **Tools**: `review` (structured findings, effort estimate, security), `describe`
  (title, walkthrough, labels), `improve` (suggestions), `ask`, `add_docs`,
  `generate_labels`. Persistent comments with finding state across runs.
- **Two token-free local modes**: `plain-diff` (`git diff | pr-agent --stdin
  --json-output …`, no PR, no clean tree) and `local` (branch vs merge-base,
  writes `review.md`). These are the strongest fit for this repo.
- **Structured output**: `--json-output` (plain-diff), the Action step output
  `outputs.review`, and `[push_outputs]` JSONL/webhook (host-only config).
- **Model routing**: `[model_routing]` picks a cheaper model for small PRs by
  hunk count, measured *after* ignore rules. All models via litellm.
- **Config precedence**: defaults < `--extra_config_url` < org
  `pr-agent-settings` repo < repo-root `.pr_agent.toml` (default branch) < env
  vars. It also auto-loads `[tool.pr-agent]` from the repo-root `pyproject.toml`.

## 2. Where it sits among what already reviews a PR

This repo already has four PR readers. PR-Agent does not replace any of them.

| reader | runs | verdict | what it is for |
|---|---|---|---|
| `pr-report.yml` (`pf pr report`) | every PR | **blocks** on `block` | blast radius, gate policy. Never says "approved" by design. |
| per-project `<project>.yml` | PRs touching that project | **blocks** (`pf air gate`, `pf impact-gate`); recce reports | baseline diff, control baseline |
| `claude-review.yml` | label `claude-review` | advisory | judgement with `pf gate` / `pf check` fed as evidence |
| CodeRabbit / Gitar (external) | every PR | advisory | generic review; findings harvested by `bot_findings.py` |

PR-Agent's slot: **the cheap, structured, persistent second reader**, with
machine-readable findings, that can also run *before* a PR exists. It stays
advisory (L1 on the `LOOP.md` ladder). `pf pr report` remains the only thing
that blocks, and `enable_auto_approval` stays `false` forever — the platform's
rule is that automation reports while a human merges.

Whether it eventually retires `claude-review.yml` is a Phase 4 question,
answered by data, not now.

## 3. Constraints that shape every phase

1. **Isolated install, never a workspace member.** `pr-agent` pins
   `litellm==1.99.0`, `pydantic==2.13.3`, `PyYAML==6.0.1`, `protobuf==6.33.6`,
   `Jinja2==3.1.6`, `tenacity==8.2.3`. Any of those in the shared `uv.lock`
   reproduces the elementary/openmetadata failure recorded in the root
   `pyproject.toml`. Pattern: `uv tool install ./vendor/pr-agent` (pinned to the
   submodule commit) locally, `docker/Dockerfile --target cli` in CI. `pf` shells
   out and imports nothing.
2. **Governed like every other agent.** Each run is a `pf.provenance.action(
   tool="pr-agent", …)`; the policy that claims it names a real symbol; the model
   is pinned and declared; `vendor/pr-agent` carries `licence_review`.
3. **Tightening only.** Any `gate` the tool contributes may add to `denylist` /
   `impact_required`; `Tool.gate_sections()` rejects anything else.
4. **Sister isolation survives review.** A project-scoped run receives that
   project's context and no sister's. A repo-scoped run sees the whole diff but
   is told that a cross-project read is a defect.
5. **The diff is attacker-controlled text.** The reviewer runs with
   `config.restricted_mode=true`, no repository write, no tools beyond reading
   the diff, and its output is a comment, never a commit. (AIR-PREV-19.)
6. **Budget.** `repo_context_files` is capped at 500 lines; project `CLAUDE.md`
   files are already budgeted by `pf tokens`. Every run records
   `output_run_cost`. A recurring run is a loop under `LOOP.md` and counts
   against the daily cap.

## 4. Repository level

### 4.1 Config: `[tool.pr-agent]` in the root `pyproject.toml`

PR-Agent auto-loads this section, so the repo needs no extra dotfile and the
config lives next to the extras and isolation notes it depends on. Contents:

```toml
[tool.pr-agent.config]
model            = "anthropic/claude-sonnet-5"      # pinned; see AGENTS routing
fallback_models  = []
restricted_mode  = true
repo_context_files = ["CLAUDE.md", "docs/CLAUDE-CODE.md"]   # ≤ 500 lines total
output_run_cost  = true
ignore_pr_authors = ["github-actions[bot]"]          # vendor-sync PRs: describe only, §4.4

[tool.pr-agent.ignore]
glob = [
  "vendor/**", "provenance/**", "graphify-out/**",
  "**/dbt_packages/**", "**/target/**", "**/target-base/**",
  "**/recce_state.json", "**/recce_summary.md",
  "**/kg/**", "**/governance/air-register.md", "**/reporting/queries/**",
  "uv.lock", "**/uv.lock",
]

[tool.pr-agent.pr_reviewer]
persistent_comment       = true
persistent_finding_state = true
num_max_findings         = 5
enable_review_labels_security = true
enable_auto_approval     = false
extra_instructions = """…router rules, see 4.2…"""

[tool.pr-agent.model_routing]
enable = true
[[tool.pr-agent.model_routing.rules]]
max_hunks = 3
model = "anthropic/claude-haiku-4-5-20251001"
```

The ignore list is the gate's generated-path list expressed as globs. Keep them
in step: Phase 3 derives this block from `gate.capabilities.yaml` instead of
hand-copying it.

### 4.2 Instructions: the router, restated for a reviewer

`extra_instructions` for `review` carries the four rules a generic reviewer
cannot know. They are the same four `claude-review.yml` already uses, so the
two stay consistent:

1. `platform/` is shared by every project. A change there is reviewed for
   *every* consumer, not the one in the PR title.
2. Business logic lives in `groups/<g>/projects/<p>/`. Anything that reads
   across groups or sister projects is a defect regardless of quality.
3. A model, column or metric change without an impact report in the PR is a
   finding; disagreeing with `pf gate` is itself a finding to raise, not to
   silently override.
4. Provenance, generated artefacts and vendored code are never hand-edited.

Domain checks (grain, fanout, null-swallowing joins, incremental predicates)
are *not* restated here. Those belong to the `sql-reviewer` subagent and the
project-level instructions in §5.

### 4.3 CI: one workflow, label-gated, GitHub Action mode

`.github/workflows/pr-agent.yml`, modelled line for line on `claude-review.yml`:

- trigger `pull_request: types: [labeled]`, `if: label.name == 'pr-agent'`;
  re-add the label to re-run. Same rationale, same billing argument.
- `permissions: contents: read, pull-requests: write`. Nothing writes to a branch.
- runs the `docker/Dockerfile --target github_action` image built from the
  submodule commit (no PyPI drift), with `ANTHROPIC_API_KEY` from repository
  secrets and the same early-exit guard when the secret is absent.
- `github_action_config.enable_output=true` and, host-side, `[push_outputs]
  channels=["file"]` so each run appends one JSON record to
  `pr-agent-outputs/reviews.jsonl`, uploaded as artifact `pf-pr-agent` next to
  `pf-pr-report`.
- comment marker `<!-- pr-agent -->`, one comment edited in place.

### 4.4 Findings lifecycle: third parser in `bot_findings.py`

`.github/scripts/bot_findings.py` already turns CodeRabbit and Gitar comments
into issues because "a review comment dies with its PR". Add a `pr-agent`
source that reads the JSON record (not the markdown), so severity and file
anchors come from the schema in `pr_reviewer_prompts.toml` rather than a regex.
Add `pr-agent.yml` to the `workflow_run` list in `bot-findings.yml`.

### 4.5 Machine-opened PRs

`vendor-sync.yml` opens a PR every Monday with `pf vendor sync` output as the
body. Run `/describe --pr_description.publish_description_as_comment=true` on
it with `model_weak`; never `/review` (the diff is a submodule bump, and the
human reading it is the point). Same for any auto-created branch PR.

### 4.6 Local, before a PR exists: `pf review`

The highest-value repo-level piece, and the one with no CI coupling:

```
pf review [--base main] [--json] [--model …]
```

Implementation `platform/src/pf/review.py`:

1. `git diff <merge-base>...HEAD` (or the working tree with `--dirty`) piped to
   `pr-agent --stdin --json-output <scratch> review` in plain-diff mode.
   Overrides passed as env (`CONFIG__…`), never by editing config.
2. Wrapped in `pf.provenance.action(root, tool="pr-agent", target=<range>,
   summary=…, group=, project=)`, with `detail` carrying model, cost, finding
   count. Same shape as `pf commit` (`docs/COMMITTER.md`).
3. Writes `data/pr/local-<sha>.review.json`; `pf ui` gets a "second reader" card
   next to the blast-radius verdict.
4. Default model: the local OpenAI-compatible endpoint `pf commit` already uses
   (`PF_COMMIT_LLM_URL`, MLX Qwen), through litellm's `openai/` provider, so the
   pre-PR pass costs nothing. `--model anthropic/…` opts into the API.

Also add the Stop-hook question: `pf review` is *not* added to the root Stop
hook. A review that runs on every session end is a loop; it needs a `LOOP.md`
entry and a budget first.

## 5. Project level

PR-Agent has no per-path config. The honest design is **one invocation per
project**, and this repo already has the machinery for exactly that: the
per-project workflows are composed from `Capability.ci_jobs`, and
`tools.yaml` decides per project whether a tool runs. So the project-level
integration is a `pf.tools` Tool, with Recce as the template.

### 5.1 `pf.tools.pragent` — the Tool declaration

`platform/src/pf/tools/pragent.py`, sixth entry in `BUILTIN_MODULES`:

| field | value |
|---|---|
| `name` | `pr-agent` |
| `scope` | `{"project", "group"}`; `default_enabled=False` (opt-in, it bills) |
| `requires` | `Requirement("binary", "pr-agent", hint="uv tool install ./vendor/pr-agent")`, `Requirement("env", "ANTHROPIC_API_KEY", …)` |
| `capability.files` | `docs/pr-agent.md` (what it reviews here, how to re-run), `.pr-agent/project.toml` (generated, §5.2) |
| `capability.ci_jobs` | `{"pr-agent": PR_AGENT_JOB}` — composed into `<project>.yml` after `impact-gate` |
| `capability.gate` | `denylist: ["**/.pr-agent/outputs/**", "**/review.md", "**/description.md", "**/improve.md"]`, `impact_required: ["**/.pr-agent/project.toml"]` |
| `capability.settings` | `permissions.allow: ["Bash(pf review:*)", "Bash(pf tool pr-agent:*)"]` |
| `commands` | `pf tool pr-agent ci <group> <project>`, `pf tool pr-agent review <group> <project>` |
| `stack_layer` | `layer: "review"`, `title: "Review (PR-Agent)"`. The UI stack table gets two rows in the review layer; that is accurate. |
| `dagster` | none. A reviewer is not an asset. |

`pf tool enable pr-agent --group hospital` turns it on for every sister;
`pf tool enable pr-agent --project hospital/mental-health` for one. Nothing else
is edited — the scaffolder, the workflow composer and the UI pick it up.

### 5.2 Scope and context per project

`bootstrap_project` renders `groups/<g>/projects/<p>/.pr-agent/project.toml`
from three inputs it already has via `ToolContext`:

```toml
[config]
repo_context_files = [
  "groups/hospital/projects/mental-health/CLAUDE.md",
  "groups/hospital/projects/mental-health/decisions/ADR-0001-grain-law.md",
]
[ignore]
regex = ['^(?!groups/hospital/projects/mental-health/)']   # everything else
[pr_reviewer]
extra_instructions = """…rendered from the project's ontology annotations…"""
```

- **Scope** is a negative-lookahead regex ignore, the one path-shaped lever
  the OSS fork honours everywhere. Model routing counts hunks *after* this, so
  a large repo PR that touches one project cheaply reviews as a small PR.
- **Context** is the project's own `CLAUDE.md` plus its ADRs, capped at the
  500-line budget by the same `pf tokens` arithmetic. Never a sister's file:
  `resolve()` takes one group and one project and enumerates nothing.
- **Instructions** are generated, not hand-written. The project's grain
  declarations, conformed dimensions and metric definitions are already in the
  ontology; render the checks the `sql-reviewer` subagent looks for (grain,
  fanout, join nulls, incremental predicates, timezone traps) as a checklist
  with the project's actual table names in it. This is also how we get the
  *effect* of `/compliance` without the missing tool: a per-project
  `compliance.yaml` (same five-field shape as upstream's example) rendered into
  `extra_instructions` at bootstrap. Its file starts with the same `GENERATED`
  marker `pf.tools.expectations` uses, so regeneration replaces only what it wrote.

The generated TOML is passed to the run with `--extra_config_url` pointing at
the raw file on the base branch (or, in the Action, mounted and read from the
default branch — never from `github.head_ref`, which upstream warns turns the
PR author into the config author).

### 5.3 The per-project CI job

`PR_AGENT_JOB` in `pragent.py`, composed into `<project>.yml` by the same path
filter (`paths: groups/<g>/projects/<p>/**`) the other four jobs use:

- `needs: [air-baseline, impact-gate]` — the deterministic gates run first;
  their step summaries are attached as evidence via `extra_instructions`,
  exactly as `claude-review.yml` attaches `platform-context.md`.
- runs `pf tool pr-agent ci <group> <project>`, which builds the env overrides
  from `.pr-agent/project.toml`, invokes the container, and records the
  provenance action with `group`/`project` set.
- posts one comment per project with marker `<!-- pr-agent:<group>/<project> -->`.
  A PR touching two sisters gets two independent, differently-scoped reviews.
- appends to the same `pf-pr-agent` artifact with the project in the record.
- label-gated at first (the `pr-agent` label), like the repo level. Moving a
  project to always-on is a `tools.yaml` setting (`pr-agent: {on_open: true}`)
  and a line in the group's `air.yaml` `accepted:` block naming the cost owner.

### 5.4 Local, inside a project session

`pf review` from a project cwd resolves the project from `PF_PROJECT_DIR`
(the same seam the MCP server uses) and applies the project TOML
automatically. The `power-tools` `ship` command gets a "second reader" step
that runs it and refuses to open the PR while a `critical` finding is
unaddressed — refuses to *open*, not to merge; the human still merges.

## 6. Governance wiring (blocks Phase 2)

| what | where | note |
|---|---|---|
| policy `pull-requests-get-a-second-reader` | `platform/src/pf/ontology/policy.yaml` | `enforced_by: [pf.tools.pragent:register_commands, pf.review:run]`, `severity: warning`, `evidence: [pr-agent-review]`, `controls: [AIR-DET-15, AIR-DET-11, AIR-PREV-19, AIR-PREV-10]` |
| evidence kind `pr-agent-review` | same file, `evidence_kinds:` | `produces: data/pr/*.review.json, pr-agent-outputs/reviews.jsonl`, `durable: true` |
| `_EVIDENCE_FILES` entry | `platform/src/pf/air/coverage.py` | so the control reads `pass`, not `unexercised`, once a run exists |
| model declaration | `pf.agents.base.AGENTS` | an `AgentConfig(name="pr-agent", model=…, purpose="second reader", cadence_minutes=None)` so `model-routing-is-declared` covers it |
| vendor registry | `platform/src/pf/vendor/registry.yaml` | `licence_review` filled; adoptions become `port` for the Action shape and `data` for `pr_reviewer_prompts.toml` (its output schema is what `bot_findings.py` parses) |
| `bot_findings.py` | `.github/scripts/` | third source, JSON-driven |
| `LOOP.md` | root | entry only if anything becomes on-open or on-Stop |

AIR-DET-15 (LLM-as-a-judge) is currently claimed by no policy. This is the
first enforcement to name it, which is the point of the exercise: the control
goes from `fail` to `pass` because a real artefact resolves.

## 7. Phases, in order

| phase | deliverable | done when |
|---|---|---|
| 0 | pin (`#330`) | merged |
| 1 | `pf review` local, plain-diff, isolated install, provenance-wrapped, local model default | `pf review --json` on a branch writes `data/pr/local-*.review.json` and `pf provenance verify` shows the action |
| 2 | governance rows (§6) + `[tool.pr-agent]` block + `pr-agent.yml` label-gated + `bot_findings.py` source | `pf air coverage` shows AIR-DET-15 `pass`; a labelled PR gets one persistent comment and one issue per surviving finding |
| 3 | `pf.tools.pragent`, `pf tool enable pr-agent` on `hospital/mental-health` only | `mental-health.yml` gains a `pr-agent` job with no edit to the workflow composer; the review cites the grain law ADR |
| 4 | measure four weeks: cost per run, findings kept vs dismissed, overlap with `claude-review` and CodeRabbit | a written decision on which readers stay, as an ADR |
| 5 | optional: `/describe` on machine PRs; `/ask` via `issue_comment`; on-open for projects that accept the cost | each behind a `tools.yaml` key and an `air.yaml` `accepted:` line |

Phase 1 has no CI, no secret, no workflow and no policy change. It can ship
from the `vendor/pr-agent` branch as a second commit, and it is where most of
the value is if the honest goal is "read my diff before I open the PR".

## 8. Explicitly not doing

- `update_changelog` with `push_changelog_changes`, committable `/improve`
  suggestions, `enable_auto_approval`: all are writes to a branch by automation.
- GitHub App / webhook server: a long-running service with repo credentials,
  for a repo with one active human. Action + CLI cover every use above.
- `similar_issue`: needs a vector DB; nothing here has one.
- Adding `pr-agent` to the uv workspace, or `litellm` to `pf`. `pf` has two LLM
  paths on purpose (raw HTTP to a local endpoint, and the `anthropic` SDK) and a
  third abstraction is a cost, not a feature.
- A shared `pr-agent-settings` org repo: config that lives outside the
  monorepo is config `pf vendor why` cannot explain.
