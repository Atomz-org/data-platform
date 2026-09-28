# AI governance & DORA compliance framework (AIDF)

The runtime governance engine every agent-written metric goes through, the
DORA (Regulation (EU) 2022/2554) evidence every entity can produce, and the
nightly issue hygiene that keeps the tracker honest — one platform layer,
`pf.aidf`, reaching every project and every project that will be scaffolded.

This page is the reference. `docs/GOVERNANCE.md` is the provenance chain the
engine writes to, `docs/AIR.md` the control catalogue the DORA audit reads,
`docs/AI-GOVERNANCE-ARCHITECTURE.md` the six planes this layer sits on.

```
                        agent (Claude · Cursor · Copilot · Gemini · Codex · local Qwen)
                                          │  MartMetricContract JSON
                                          ▼
   ┌─── pillar 1 · pf govern ──────────────────────────────────────────────────┐
   │ budget → breaker → action gate → contract → SQL AST → catalogue → PII    │
   │            │           │                                    │             │
   │       provenance/  gate.yaml + aidf.yaml roles         kg/graph.json      │
   │                                                                          │
   │  every outcome: INTENT → DECISION → EXECUTION, SHA-256 linked, anchored   │
   │  PASS · REJECT · ESCALATED · CIRCUIT_BROKEN                               │
   └──────────────────────────────────────────────────────────────────────────┘
                                          │  governance/metrics/<mart>/<metric>.json
                                          ▼
   ┌─── pillar 2 · pf dora ────────────────────────────────────────────────────┐
   │ Prowler (Art. 8-11) · Trivy + patch policy (RTS Art. 10) · provenance    │
   │ (Art. 12) · repository & CI (Art. 17, 24, 25, RTS Art. 16) · vendor pins │
   │ (Art. 28)  →  governance/dora/matrix.{json,md}, hash recorded to chain   │
   └──────────────────────────────────────────────────────────────────────────┘
   ┌─── pillar 3 · issue hygiene ──────────────────────────────────────────────┐
   │ lexical + semantic duplicates · labels → board fields, every open issue   │
   └──────────────────────────────────────────────────────────────────────────┘
```

## Where the specification landed

The blueprint this was built from names a root-level `governance/` package, a
`compliance/` tree, a per-block `provenance/chain_000001.json` ledger and three
new workflows. This repository already had the ledger, the path gate, the
control catalogue and the issue sweep, and a router rule that shared machinery
lives under `platform/` and reaches projects through capabilities. So the
blueprint's components landed where the platform keeps that kind of thing:

| blueprint | here | why |
|---|---|---|
| `governance/schemas/*.py` | `platform/src/pf/aidf/schemas.py` | Pydantic v2 strict, frozen, no extras; the mart pattern is per entity, through validation context |
| `governance/validators/ast_sql_validator.py`, `pii_scrubber.py` | `pf/aidf/validators.py` + `pf/aidf/guardrails_adapter.py` | pure Python, no Guardrails import; the adapter registers `atomz/ast_sql_validator` and `atomz/pii_scrubber` when the package is present |
| `governance/gate_enforcer.py` | `pf/aidf/gate.py` over `pf.loops.gate` | one path policy (`gate.yaml`), consulted first; roles and elevation from `aidf.yaml` |
| `governance/provenance.py`, `provenance/chain_*.json` | `pf.provenance` (unchanged) | the chain already existed with five stages and RFC 3161 + OpenTimestamps anchors; a second ledger is what AGENTS.md §7 forbids |
| `governance/circuit_breaker.py` | `pf/aidf/breaker.py` | state is *read from the chain*, never a side file: a restart cannot forget it, a delete cannot reset it |
| `governance/engine.py` | `pf/aidf/engine.py` | the same order — gate, contract, validators, ledger, write — with every branch recorded |
| `compliance/dora/config.yaml`, `mappings.json`, `rts_patch_policy.yaml` | `pf/aidf/data/{defaults.yaml,mappings.json,prowler.yaml}` + per-entity `governance/aidf.yaml` | the statute is platform data; scope, cloud, owner and exceptions are the entity's |
| `compliance/dora/run_audit.py` | `pf dora audit` (`pf/aidf/dora/audit.py`) | runs or ingests Prowler and Trivy, judges every check, writes the matrix, records it |
| `compliance/reports/` | `groups/<g>/projects/<p>/governance/dora/` | generated, gitignored, archived by CI, SHA-256 in the chain |
| `gate.yaml` `policies:` block | `gate.yaml` (unchanged) + `aidf.yaml` `runtime.roles` / `elevated` | path rules stay in the one gate; role authorisation is entity configuration |
| `loop-constraints.md`, `LOOP.md`, `STATE.md` | unchanged | already binding, already read by every loop |
| `ai_governance_gate.yml`, `provenance_integrity.yml` | `ai-governance.yml` — new job `runtime-governance` | the provenance job already existed there |
| `dora_compliance_audit.yml` | `dora.yml` | nightly + dispatch + pull requests that touch the lockfile |
| `issue_management.yml`, `scripts/manage_issues.py` | `issue-hygiene.yml` + `.github/scripts/issue_hygiene.py` (extended) | the nightly sweep existed; two passes were added rather than a second cron racing it |

## Pillar 1 — runtime governance

### The entity model

Everything is resolved from `(group, project)`. Three layers, each tightening
the one before, loaded by `pf.aidf.config.load`:

```
platform/src/pf/aidf/data/defaults.yaml                    the floor, every entity
groups/<group>/aidf.yaml                                   the family (optional)
groups/<group>/projects/<project>/governance/aidf.yaml     the entity (seeded by the `aidf` capability)
```

A project with no overlay at all resolves to the floor. That is the guarantee
for projects scaffolded before this existed and for every one `pf new-project`
creates: the `aidf` capability is default-enabled, `pf bootstrap` backfills
its seeded file, and the file is inert on arrival.

Tightening is enforced at load time and raises `AidfRelaxation`:

| may only … | keys |
|---|---|
| go down | `runtime.budgets.*`, `dora.prowler.fail_on.*`, `dora.sbom.grace_days.*` |
| grow | `runtime.validators`, `runtime.system_schemas`, `runtime.elevated.paths`, `dora.sbom.severity` |
| switch on | `runtime.budgets.trip_circuit_breaker_on_breach` |
| switch off | `dora.sbom.ignore_unfixed` (off blocks on unpatchable findings too) |
| catch more | `dora.prowler.severity_threshold` |
| be declined with reason + owner | `dora.in_scope`, `dora.articles.<id>.applies` |
| be dated and owned | `dora.sbom.exceptions[]` |

### The evaluation

```
pf govern evaluate <group> <project> --payload proposal.json --role metric-gap-harvester
```

| step | refuses when | recorded as |
|---|---|---|
| budget | more than `max_iterations_per_invocation` evaluations in one process | `BudgetExceeded` (not a ledger entry; the process is at fault) |
| breaker | `max_consecutive_validation_failures` REJECTs with no PASS between | `CIRCUIT_BROKEN` — decision `deny aidf:circuit_breaker`, execution `blocked` |
| gate | target escapes the project, is immutable (`provenance/`, `.github/`, `gate.yaml`, `LOOP.md`…), is denied by `gate.yaml`, or the role may not write there | `REJECT` — decision `deny <rule>`, execution `blocked` |
| elevation | target matches `elevated.paths` and the role is not in `elevated.roles` | `ESCALATED` — decision `hold human_oversight`, execution `blocked`; approve with `pf provenance approve <action_id>`, resubmit `--approved <action_id>` |
| contract | strict JSON: wrong type, unknown field, bad identifier, naive timestamp, mart outside the entity's pattern | `REJECT` — `deny aidf:schema` |
| SQL AST | DDL/DML, a second statement, `SELECT *`, a system catalogue, a file-reading function, a column or table the catalogue lacks, a column read but not declared | `REJECT` — `deny aidf:sql_ast` |
| PII | e-mail, IPv4, IBAN, bearer/JWT, cloud key, private key, `password =` in any string field | `REJECT` — `deny aidf:pii` |
| write | — | `PASS` — decision `allow`, execution `ok`, the record under `governance/metrics/<mart>/<metric>.json` |

What the ledger carries about a payload is its SHA-256 and the findings — never
the payload. The PII finding names the kind and the offset of a match, not the
match; a rejection record cannot become the leak it prevented.

The catalogue for the hallucination check is the entity's own knowledge graph
(`kg/graph.duckdb`, then `kg/graph.json`, then dbt's manifest). When none is
available the validator reports `catalog: absent` in the decision record; it
does not pass silently.

### Commands and tools

```
pf govern check [group [project]]      every entity's resolved config; refuses one that loosens the floor
pf govern schema [mart_metric|semantic_model]
pf govern prompt <group> <project> <mart> <metric>     the dispatch prompt with this mart's columns
pf govern evaluate <group> <project> --payload f.json --role R [--target rel] [--contract c] [--no-write] [--json]
pf govern breaker <group> <project> [--reset --reason "..."]
```

Exit codes: `0` PASS, `1` REJECT, `2` ESCALATED, `3` CIRCUIT_BROKEN.

MCP: `govern_metric(payload_json, role, target="", contract="mart_metric")` and
`govern_prompt(mart_name, metric_name)` on the `pf` server — the same engine for
every harness that speaks MCP, which is how the framework is model-agnostic
without a per-vendor code path.

Python: `GovernanceEngine(root, group, project).evaluate(payload, role=...)`
returns an `Outcome`; `pf.aidf.schemas.validate_payload` is the contract alone.

### Directives per scope

Rules go by how a tool was invoked (AGENTS.md §0), not by whose model it runs.
`pf.aidf.prompts.DIRECTIVES` is the source; in short:

- **Session** (Claude Code, Codex CLI, Cursor agent, Gemini CLI…): produce
  contract JSON and submit it through `pf govern evaluate` or `govern_metric`;
  never write under `governance/metrics/` by hand; run `pf dora audit` before
  claiming compliance.
- **Autonomous** (`@claude` in Actions, Jules, Copilot coding agent): a REJECT
  is final for the run — fix the payload, never the rule; ESCALATED waits for
  a person; CIRCUIT_BROKEN ends the run, and the issue or PR says so.
- **Inline** (completions): reference only columns the file or
  `kg/architecture.md` already names; never DDL/DML; never `provenance/`,
  `gate.yaml`, `LOOP.md`, `.github/`; leave `NOTE(memory):` for the session.
- **Local model** (Qwen on mlx/Ollama through OpenCode or Codex): emit a
  verification block naming the tables and columns you intend to use and
  confirm each against the approved list before the JSON.
- **CI glue** (any model writing workflows): `uv run` / `uv sync` / `uvx`
  only; commands like prowler, trivy and guardrails are installed isolated,
  never added to the workspace lockfile.

The dispatch prompt (`pf govern prompt`) embeds the contract's JSON schema, so
what a model is told and what judges it cannot drift apart.

## Pillar 2 — DORA evidence

### The statutory matrix

`pf dora matrix` prints it from `platform/src/pf/aidf/data/mappings.json`;
this table is a summary. Each check has a *kind*, and the kind says what
evidence it needs and what `unverified` means for it.

| article | requirement | checks (kind) |
|---|---|---|
| Art. 5 Governance | accountable owner, framework approved | `dora.owner` declared; entity `governance/policy.yaml` present |
| Art. 6 ICT risk framework | documented, reviewed | `air.yaml` baseline committed (air); `loop-constraints.md` present |
| Art. 7 Systems & tools | reliable, resilient | CycloneDX SBOM (trivy); `vendor.lock.json` |
| Art. 8 Identification | asset inventory | Prowler inventory/config checks; entity `kg/graph.json` |
| Art. 9 Protection & prevention | IAM, MFA, encryption, network | Prowler IAM/KMS/secrets; Prowler security groups/VPC; `gate.yaml` denies credential paths |
| Art. 10 Detection | logging, alerting | Prowler CloudTrail/GuardDuty/…; `LOOP.md` monitors |
| Art. 11 Response & recovery | backups, continuity | Prowler backup/versioning; provenance kill switch |
| Art. 12 Backup & restoration | integrity-protected records | provenance chain integrity; anchor coverage |
| Art. 13 Learning | lessons, vulnerability intelligence | `.memory/MEMORY.md`; nightly Trivy scan |
| Art. 14 Communication | channels | `groups/<g>/notify.yaml` |
| Art. 17 Incident management | detect, record, notify | `loop-observations.yml`; `bot-findings.yml` |
| Art. 24 Resilience testing | programme, independent, remediated | `platform-tests.yml` runs the suite; `ai-governance.yml` runs `pf provenance verify` |
| Art. 25 Testing of tools | scans, reviews, penetration | `dora.yml` runs the audit; no fixable Critical/High past its window |
| Art. 28 Third-party risk | register, due diligence | `pf/vendor/registry.yaml`; `vendor-pins.yml` drift check |
| RTS Art. 10 Vulnerability & patch | risk-based windows | patch policy over the Trivy scan |
| RTS Art. 16 Acquisition & development | secure SDLC, segregation | branch protection (live); pre-commit gate; `pf govern check` in CI |

Statuses per check: `pass`, `fail`, `unverified` (the check could not run
here — a tool missing, no scan, no ledger; never counted as a pass),
`not_applicable` (declared out of scope with a reason and an owner). Overall:
`pass`, `pass_with_gaps`, `fail` (exit 1), `not_applicable`.

### Running it

```
pf dora audit <group> <project>                       run what is on PATH, judge everything, write the matrix
pf dora audit <group> <project> --ocsf prowler.ocsf.json --vulns trivy.json --sbom sbom.cdx.json --no-run
pf dora audit                                         every entity in the checkout
pf dora audit <group> <project> --live                also read branch protection through gh
pf dora check                                         matrix well-formed, every entity's config resolves (CI)
```

Outputs land in `groups/<g>/projects/<p>/governance/dora/` — `matrix.json`,
`matrix.md`, and the scans they were judged from. The directory is generated
and gitignored; CI archives it (400-day retention) and the audit is recorded to
the provenance chain as action `aidf.dora` carrying the matrix's SHA-256. The
JSON names the action id and the hash, so a report and the chain cite each
other.

Prowler and Trivy are *commands*, installed isolated — the same rule as
`openmetadata-ingestion` and the Elementary CLI, for the same reason (one
workspace lockfile cannot hold their SDK pins beside dlt and dagster):

```
uv tool install prowler            # or pin: uv tool install "prowler==5.10.0"
brew install trivy                 # or aquasecurity/setup-trivy in CI
```

If the installed Prowler lists no `dora_2022_2554` framework for the provider,
the audit runs the full check set and maps findings to articles by check-id
prefix from the matrix; the note appears in the report.

### Per-entity configuration

`governance/aidf.yaml` under the project (seeded by the capability):

```yaml
dora:
  owner: risk@example.com            # Art. 5
  provider: aws                      # aws | azure | gcp | kubernetes; empty = no infrastructure scan
  sbom:
    exceptions:
      - id: CVE-2026-0001
        reason: Not reachable; the affected code path is never imported.
        owner: platform@example.com
        expires: 2027-01-01
  articles:
    "28":
      applies: false
      reason: No ICT third-party provider holds this entity's data.
      owner: risk@example.com
```

An entity outside DORA's scope says so:

```yaml
dora:
  in_scope: false
  out_of_scope_reason: Not a financial entity or critical ICT provider under Art. 2.
  owner: legal@example.com
```

and its audit reports `not_applicable`, with the reason printed, never `pass`.

### CI — `.github/workflows/dora.yml`

| job | when | does |
|---|---|---|
| `supply-chain` | nightly 02:00 UTC · dispatch · pull requests touching `uv.lock`, `pyproject.toml`, `**/governance/aidf.yaml`, `pf/aidf/**` | Trivy SBOM + scan, then `pf dora audit` for every entity; exit 1 blocks the PR on a fixable Critical/High past its window |
| `infrastructure` | nightly · dispatch, never on a pull request | `uv tool install prowler`; the cloud scan for `vars.DORA_PROWLER_PROVIDER` with its credential; the GitHub posture scan when `secrets.DORA_GITHUB_TOKEN` is set; one `pf dora audit` over every scan that ran; a warning when nothing is configured |

Both archive `governance/dora/**`, the scans and `provenance/chain.jsonl` as
one artifact. The `runtime-governance` job in `ai-governance.yml` runs the
engine's attack tests, `pf govern check` and `pf dora check` on every pull
request.

#### Configuring the scans

Variables are plain text and visible in logs; tokens and keys are secrets.
Both live under the repository's Settings, "Secrets and variables", "Actions"
(or `gh variable set` / `gh secret set`).

| setting | kind | value |
|---|---|---|
| `DORA_PROWLER_PROVIDER` | variable | the cloud Prowler audits: `aws`, `azure`, `gcp` or `kubernetes`. Never a token. |
| `DORA_GCP_WORKLOAD_IDENTITY_PROVIDER` + `DORA_GCP_SERVICE_ACCOUNT` | secrets | keyless GCP auth: the pool provider resource name (`projects/<n>/locations/global/workloadIdentityPools/<pool>/providers/<p>`) and the service account e-mail it may impersonate. Preferred. |
| `DORA_GCP_CREDENTIALS_JSON` | secret | a service-account key, only when no federation is set up |
| `DORA_GCP_PROJECT_IDS` | variable | optional, space-separated project ids to scan; empty scans every project the account can see |
| `DORA_AWS_ROLE_ARN`, `DORA_AWS_REGION` | secret, variable | the OIDC role for `aws` and its region |
| `DORA_KUBECONFIG_B64` | secret | a base64 kubeconfig for `kubernetes` |
| `DORA_GITHUB_TOKEN` | secret | a fine-grained PAT for the GitHub posture scan: organisation members and administration read, repository administration and metadata read, Actions read. The run's own `GITHUB_TOKEN` cannot see organisation settings. |
| `DORA_GITHUB_ORGANIZATION` | variable | optional; defaults to the repository's owner |

The GCP service account needs Prowler's documented read-only roles on the
scanned projects or the organisation: `roles/viewer` plus
`roles/iam.securityReviewer`, and the APIs Prowler reads enabled. The
workload-identity route needs the pool provider to trust
`repo:Atomz-org/data-platform:ref:refs/heads/main` (and any branch you
dispatch from). Nothing else has to change for a new project: the scan is per
account, the audit is per entity, and each entity's `governance/aidf.yaml`
says which provider and extra providers apply to it.

## Pillar 3 — issue hygiene

`issue-hygiene.yml` (01:00 Europe/Oslo nightly) already merged lexical
duplicates among review findings and filled the sidebar. Two passes were added:

- **Semantic duplicates.** With `sentence-transformers` (installed isolated by
  `uv` in the workflow and cached; `vars.HYGIENE_EMBEDDINGS=off` disables it)
  every pair of open findings is compared by embedding cosine: ≥ 0.85 closes
  the newer as a duplicate of the older, ≥ 0.75 labels `possible-duplicate`.
  Same guards as the lexical pass: never a bundle, never across files, never a
  `not-duplicate` pair. Without the package the pass is skipped and says so.
- **Labels → project fields, every open issue.** `priority:*`, `effort:*` and
  `area:*` set the board's Priority, Effort and Category through the ProjectV2
  GraphQL API (`DEFAULT_FIELD_MAP`; override with `vars.HYGIENE_LABEL_FIELDS`
  as `{field: {label: option}}`). Needs `PROJECTS_TOKEN`.

The workflow now declares `repository-projects: write`. `DRY_RUN=1` (the
default for a manual dispatch) prints every change and touches nothing, the
board included.

## Supply chain: the Atomz-org forks

Both frameworks the blueprint names are pinned the way every other upstream
here is pinned — our own forks under `Atomz-org`, shallow submodules under
`vendor/`, registered in `platform/src/pf/vendor/registry.yaml`, reviewed into
`vendor.lock.json`, indexed in `docs/VENDOR-CARD.md`:

| pin | at | licence | what we take |
|---|---|---|---|
| `vendor/guardrails` | guardrails-ai 0.11.0 (fork head 2026-08-26) | Apache-2.0 | `guardrails/validator_base.py` (`port`), `guardrails/guard.py` (`shape`) |
| `vendor/prowler` | prowler 5.44.0 (fork head 2026-09-28) | Apache-2.0 | `prowler/lib/outputs/ocsf/ocsf.py` (`parity`), `prowler/compliance/dora_2022_2554.json` (`parity`), `prowler/lib/cli/parser.py` (`shape`) |

`pf vendor verify` checks the paths still exist at the pin, `pf vendor drift`
names the files of ours to re-read when a bump moves them, and the parity tests
in `platform/tests/gate/test_aidf_dora.py` check the matrix against the pinned
framework itself. Bumping either pin is `git submodule update --remote` plus
`pf vendor approve` in a reviewed pull request — a human's, as the router says.

**Neither is a workspace dependency, by design.** Both pin dependency ranges
(litellm, openai and langchain-core; boto3 and the Azure and Google SDKs) that
one resolution cannot hold beside dlt, dagster and dbt; the repository already
paid that price with `openmetadata-ingestion` and documents it in
`pyproject.toml`. So they are a *command* and an *optional import*, from the pin:

```bash
# Prowler — a command, isolated. From PyPI at the pinned version, or from the pin itself:
uv tool install "prowler==5.44.0"
uv tool install --editable ./vendor/prowler

# Guardrails — an optional import for the adapter, per invocation:
OTEL_SDK_DISABLED=true uv run --with ./vendor/guardrails python -c \
  "from pf.aidf.guardrails_adapter import build_guard; print(build_guard({'amount'}))"
```

Nothing in the engine or the audit changes either way: the validators are pure
Python, the adapter activates when `guardrails` imports, the audit finds
`prowler` on PATH.

What pinning the real code taught, and what the code now does about it:

- **Guardrails 0.11 renamed `Guard.from_pydantic` to `Guard.for_pydantic`**, and
  `Guard.use()` *replaces* the validators on a path rather than adding to them.
  The adapter uses whichever constructor exists and binds validators per field
  (`on="$.sql_definition"`), so the SQL validator sees the SQL and not the JSON
  around it. Proven against the pin: a `DROP TABLE`, a column the catalogue
  lacks and an e-mail address in the rationale each raise; a clean payload
  parses.
- **Guardrails phones home.** It exports OpenTelemetry spans to a Guardrails
  endpoint by default; `OTEL_SDK_DISABLED=true` (or `guardrails configure
  --disable-metrics`) keeps a governance check from becoming an outbound call.
- **Prowler ships a DORA framework** — `prowler/compliance/dora_2022_2554.json`,
  universal across aws, azure, gcp, alibabacloud and cloudflare (not
  kubernetes), with requirement ids `DORA-Art5` … `DORA-Art45`. A scan run with
  `--compliance dora_2022_2554` stamps every finding with the ids it evidences
  under `unmapped.compliance["DORA-2022/2554"]`, and the audit maps findings to
  articles by those ids first, falling back to check-id prefixes only when the
  stamp is absent (a scan run without the framework, or kubernetes).
- **Prowler's `github` provider reads the organisation itself** — branch
  protection, required reviews, signed commits, secret and dependency scanning,
  Actions permissions, members' MFA. GitHub is not in the DORA framework file,
  so those findings map by check-id prefix: the repository checks to RTS Art. 16
  (`rts-16-github-posture`), the organisation access checks to Art. 9. One audit
  takes several scans (`--ocsf gcp.ocsf.json --ocsf github.ocsf.json`) and
  judges each finding by the provider it came from; an entity lists the extra
  scans that apply to it under `dora.extra_providers`.

If a future decision does want them resolvable in the workspace, the wiring is
a `[tool.uv.sources]` block with an extra, made together with a fresh
`uv lock` whose resolution is reviewed:

```toml
[project.optional-dependencies]
guardrails = ["guardrails-ai"]
compliance = ["prowler"]

[tool.uv.sources]
guardrails-ai = { path = "vendor/guardrails", editable = true }
prowler = { path = "vendor/prowler", editable = true }
```

## Runbook

```bash
uv sync --frozen
uv run pytest platform/tests/gate/test_aidf_config.py platform/tests/gate/test_aidf_validators.py \
              platform/tests/gate/test_aidf_engine.py platform/tests/gate/test_aidf_dora.py -q
uv run pf govern check                               # every entity resolves, only tightening
uv run pf dora check                                 # matrix well-formed
uv run pf provenance verify                          # the chain the engine writes to
uv run pf govern schema mart_metric > /tmp/schema.json
uv run pf govern prompt jaffle jaffle-shop orders order_count
echo '{"mart_name":"orders","metric_name":"order_count","aggregation_type":"COUNT","sql_definition":"SELECT COUNT(order_id) FROM orders","dependent_columns":["order_id"],"author_agent":"metric-gap-harvester"}' \
  | uv run pf govern evaluate jaffle jaffle-shop --payload - --role metric-gap-harvester --no-write
uv run pf dora audit jaffle jaffle-shop              # matrix in groups/jaffle/projects/jaffle-shop/governance/dora/
```

## What is deliberately different from the blueprint

- **One ledger, not two.** Governance outcomes are records in the existing
  five-stage chain, in the deny/blocked pairing `pf provenance verify` checks.
- **The breaker has no file.** Its count is derived from the chain; a reset is
  a recorded action with a reason.
- **Roles live in configuration, paths in the gate.** `gate.yaml` keeps its
  shape; `aidf.yaml` adds who may write where and what needs a person.
- **Contracts are validated in strict JSON mode.** Strict Python mode would
  demand enum instances and datetime objects, which no model emits.
- **`unverified` exists.** A check that could not run is reported as such,
  never as a pass — the blueprint's runner returned 0 when Prowler wrote no
  report.
- **The mart pattern is per entity.** `^adv_…` was one project's convention;
  the floor accepts snake_case and the entity tightens it.
- **Article numbering follows the statute.** Network security sits under
  Art. 9, learning under Art. 13, secure development under RTS Art. 16, patch
  management under RTS Art. 10 (Delegated Regulation 2024/1774).
- **Scanners and Guardrails are not workspace dependencies.**
- **No second nightly cron for issues.** The existing sweep gained two passes;
  a second job over the same issues would race it.

## Known gaps

- The check-id prefix tables in `mappings.json` are the fallback for scans
  without the DORA stamp and for kubernetes; a parity test pins each prefix to
  a real Prowler service, but the article each one *belongs* to is our reading,
  not the framework's.
- `rts-16-branch-protection` needs `--live` and a token; the nightly job
  passes both, pull requests do not.
- Prowler is pinned but not installed in a developer checkout; the audit
  reports it `not installed` there and `unverified` for Articles 8-11 until
  `uv tool install` or the nightly job runs it.
- The harness maps are at their token budget (jaffle-shop 3999/4000); the
  next workflow or capability added needs the renderer to cap a section.
