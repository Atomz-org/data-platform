# LOOP.md — loop definitions

Building blocks adapted from [loop-engineering](vendor/loop-engineering).
The patterns there are software-delivery loops; a data platform watches different
subjects — freshness, drift, metric coverage, index staleness.

Run: `pf loop list [group project]` · `pf loop run <loop> <group> <project> [--notify]` · `pf loop run-all <group> <project>`
Govern: `pf loop ladder` · `pf loop promote|demote|revert` · `pf loop proposals` · `pf loop memory` · `pf loop audit` · `pf gate --paths <a,b>`

## Autonomy ladder

A loop is **born** at a level (the registry) and **earns** the next one (the
ledger). The two are separate on purpose: the registry changes in a pull
request; a level is a fact about a track record and lives in `loop-levels.json`
next to the ledger that proves it.

| Level | Meaning | Earned by |
|---|---|---|
| **L1** | Report only. Proposals are *recorded*, never branched. | Default for every loop. |
| **L2** | Proposals become reviewed pull requests: gate → worktree → commit → impact → Recce → PR. Never a merge. | ≥ 20 clean runs in 30 days, 0 failures in the last 10, contract evals passing. |
| **L3** | Unattended. | ≥ 50 clean runs in 60 days, 0 reverted patches, live eval pass rate ≥ 0.95 within 14 days. **Nothing is L3 yet**, and the merge step does not exist in code until something is. |

- `pf loop ladder <group> <project>` shows what each loop has earned and what
  still blocks the next rung. Promotion is computed, then a **human confirms**
  (`pf loop promote`). `--force` works and is recorded as forced, with a name.
- **Demotion is automatic.** `pf loop revert <loop> … --note` records that a
  person reverted something the loop wrote; the loop drops a rung and earns it
  back from zero. One revert outweighs any number of quiet runs.
- Promotion and merge read the **same eval scores** (`data/evals/latest.json`,
  written by `pf evals-gate`). A loop cannot climb on evidence a merge would refuse.

## Loops

| Loop | Owner | Cadence | Born | Budget/run | Writes | Subject |
|---|---|---|---|---:|---|---|
| `freshness-triage` | registry | every 2h | L1 | 4,000 | no | stale sources, volume anomalies |
| `test-failure-triage` | registry | on dbt failure | L1 | 12,000 | proposes | classify failing nodes; when the cause is `model_logic`/`test_too_strict` with high confidence, draft the fix as a proposal |
| `metric-gap-harvester` | registry | daily | L1 | 8,000 | no | marts with no metric coverage |
| `pii-audit` | registry | daily | L1 | 0 | no | PII reaching a mart unmasked |
| `impact-sentinel` | registry | pre-commit | L1 | 0 | no | blast radius of uncommitted changes |
| `index-refresher` | registry | on manifest change | L2 | 0 | yes | rebuild graph + context card |
| `vendor-drift` | registry | weekly | L1 | 0 | no | vendored upstreams that moved |
| `dashboard-coverage` | `evidence` tool | daily | L1 | 0 | no | metrics no page shows; pages naming metrics that do not exist |

A tool contributes loops through its `Tool.loops` hook; `pf loop list` merges
them with the registry. A loop about a tool's artefacts belongs to the tool.

Daily budget across all loops: **200,000 tokens**. The circuit breaker opens on
depletion, or after 3 consecutive failures of the same loop.

## Anatomy of a run

```
schedule → constraints → state (STATE.md) → circuit breaker → body
        → memory (decisions/loop-memory.yaml)      drop what the project already decided
        → proposals at the earned level            L1 record · L2 branch+impact+Recce+PR
        → gate.yaml → ledger (loop-ledger.json) → STATE.md → escalate or stop
```

### Closing the loop

A body may call `run.propose(Proposal(...))` with whole-file contents. The runner
executes proposals *after* the body returns, through `pf.loops.actions`:

1. every path through the gate — one deny stops the run (`gate_blocked`);
2. at L1, the proposal is recorded in `data/proposals/` and nothing else — this
   is how an L1 loop shows what it *would* have done, which is the promotion evidence;
3. at L2, a `git worktree` on `loop/<loop>/<id>` (the operator's checkout is never
   touched), one commit, the impact report from the branch's real diff, Recce if
   installed, `gh pr create` if `gh` and a remote exist — else the branch is left
   and the proposal says so.

`pf loop proposals list|accept|reject` is where a person closes it. `accept`
lands on the ledger and counts toward promotion; `revert` is the stronger signal.

### Memory

`groups/<g>/projects/<p>/decisions/loop-memory.yaml` — what the project has
decided about its own findings. An entry is a pattern, a loop (or `*`), a
**required** note, and optionally an expiry. `suppress` drops the finding;
`annotate` keeps it with the note attached. Reviewed in pull requests like any
decision; `pf loop memory audit` lists suppressions with no expiry and entries
that never fire. Memory filters findings only — it cannot name a file or loosen
a budget, and the loader rejects keys it does not know.

### Trace logs — `logs/trace/`

Every loop run, question, proposal chain and `align ship` writes one JSONL
transcript (`logs/trace/<date>/<kind>-<name>-<id>.jsonl`, indexed in
`logs/trace/index.jsonl`): the **intent** (why the step exists), what the agent
**understood** (every agent schema carries an `understanding` field it must
fill), the **request** (model, params, the full user prompt, a hash of the
cached prefix), the typed **response** and usage, each **tool call** and
**tool result**, each deterministic **step** (breaker, memory, gate, branch,
impact, review, PR, record), each **finding** and **proposal**, and the
**outcome**. `pf logs list|show <run>|tail` read them. Secrets are redacted;
`PF_TRACE=0` turns writing off. Gitignored — the ledger is what is committed.

### Reaching every project

The agentic layer is the `loops` capability (default-enabled): `pf new-project`
applies it, `pf bootstrap` backfills it into projects created before it
existed — `decisions/loop-memory.yaml`, `docs/loops.md`, session permissions
and gate rules — and writes the group's `notify.yaml`. Nothing in it is
company-specific; no business logic is carried between entities.

### Delivery

`--notify` on `run`/`run-all`/`ask` posts to the group's incoming webhook
(`groups/<g>/notify.yaml`, channels `loops` / `ask` / `default`, or
`PF_NOTIFY_WEBHOOK`). Slack and Teams both accept the payload.

CI pushes observations to the issue board: the `loop observations` workflow
(daily, on merge to main, on dispatch) runs the deterministic loops against
every project and files each observation as an issue — label
`loop-observation`, one per loop × project, updated in place, closed on the
next clean run, with the trace logs attached to the workflow run as an
artifact. With a `PROJECTS_TOKEN` secret the issues also land on the
"Platform observations" ProjectV2 board. `.github/scripts/loop_observations.py`
shares its conventions with `bot_findings.py`.

## The other surfaces

- **`pf ask <group> <project> "<question>"`** — a business question answered from
  governed metrics only. The agent has `list_metrics`, `get_dimensions`,
  `query_metrics` and no SQL; it names the metric, dimensions and filter, links
  the governed page, and says "no metric covers this" rather than guessing from a
  table. `--direct` is the no-model form `<metric> [by <dimension>]`. Also an MCP
  tool: `ask_metric_question`.
- **`pf evals-gate [group project] [--live]`** — evals as a merge gate. Required
  when the diff touches the agent surface (prompts, routing, skills, loop
  registry, MCP server, `.gitmodules`); prompt/skill edits additionally require
  `--live`. `pf gate` (pre-commit) and `pf check` (CI) run the contract tier
  automatically on those paths.
- **`pf align ship`** — one validated onboarding stage as one PR, scoped to the
  files the stage owns, through the same chain a loop proposal takes.
  **`pf align funnel`** — time-to-first-governed-metric per project, read from
  the ledger.

## Failure modes catalogued

- **Agent skips the impact gate.** Observed in this repo: staging was regenerated,
  three marts broke, zero impact reports in the window. Fixed by moving the gate
  into `pf check`, the pre-commit hook and the PreToolUse hook.
- **Loop retries a broken fix forever.** Bounded by `escalate_after: 3`, counted
  in the ledger so a restart does not reset it.
- **A loop edits shared infra.** Blocked by `platform_denylist` in `gate.yaml`.
- **Sister contention on the tracking DB.** Bounded lock-retry in `pf.obs`.
- **A loop is promoted on enthusiasm.** Promotion is computed from the ledger and
  the recorded eval score, and needs a named human; a forced promotion says so.
- **A correct finding becomes noise.** Memory, with a required reason and an
  audited expiry — so a suppression is a visible decision, not a lost alert.
- **A prompt change ships green.** The eval gate fires on the agent surface, the
  same way impact fires on a model.
