# The committer

Commit segregation by a locally served model, so the session implementing
logic never spends attention on git splits. `pf.committer` is the module;
`pf commit` is the seam.

## The division of labor

The model — local weights, no tokens, no code leaving the machine — reads the
working tree and proposes how it splits into commits: groups of files, a
message each, as JSON. Everything around that proposal is deterministic and
not the model's to decide:

| Step | Who | What |
|---|---|---|
| survey | git | every pending change, untracked listed individually, submodule-internal churn invisible |
| split | the model | groups + messages, JSON only — it runs no command and touches no file |
| validation | `pf.committer:validate_plan` | every change assigned exactly once; invented paths refused; `vendor/**` and `.gitmodules` refused (a pin bump is a human decision); gate-denied paths refused |
| apply | git | ordinary commits — the pre-commit impact gate still fires |
| record | provenance | one action per commit (sha in the execution record) + a `Commit-Split-By:` trailer in the message |

A plan that fails validation is printed and dropped. A hallucinated path is an
error message, not a staged change.

## Commands

```bash
pf commit               # propose: print the plan, save it to data/commit_plan.json
pf commit --apply       # make exactly the saved plan's commits (re-plans if the tree moved)
pf commit --auto        # plan and apply in one shot — for hooks and scripts
```

The saved plan carries a fingerprint of the tree it described; any edit,
commit or new file invalidates it, so `--apply` can never commit a split that
was reviewed against a different tree.

## The backend

Any OpenAI-compatible server on this machine. The default is `mlx_lm.server`
with Qwen, **thinking disabled** — measured on this task, a reasoning-enabled
Qwen spends its entire token budget thinking and returns a message with no
content at all (`finish_reason='length'`), so the switch is not an
optimisation:

```bash
uv run --with mlx-lm mlx_lm.server \
  --model mlx-community/Qwen3.5-9B-MLX-4bit \
  --chat-template-args '{"enable_thinking":false}'
```

| Variable | Default | Meaning |
|---|---|---|
| `PF_COMMIT_LLM_URL` | `http://127.0.0.1:8080/v1/chat/completions` | the completions endpoint (LM Studio `:1234`, Ollama `:11434/v1`) |
| `PF_COMMIT_LLM_MODEL` | `mlx-community/Qwen3.5-9B-MLX-4bit` | model id, also the attribution name |
| `PF_COMMIT_LLM_TIMEOUT` | `180` | seconds before the local call is abandoned |
| `PF_COMMIT_BACKEND` | `local` | `claude` forces headless `claude -p` (haiku) |
| `PF_AUTO_COMMIT` | *(unset)* | `1` arms the session-end hook |

A local server that is down is an everyday state, not an error: the call
falls through to headless `claude -p --model haiku` when that CLI is
installed, and only fails when neither answers. Whichever backend answered is
the name in the trailer. One trap on the fallback: a stale `ANTHROPIC_API_KEY`
in the environment shadows a claude.ai login and the CLI 401s — the error
surfaces the CLI's own words so this diagnoses itself.

## The style guide seam (NotebookLM or any curated brief)

Twelve log subjects teach the model less than a curated page. If
`docs/COMMIT-STYLE.md` exists (override the location with
`PF_COMMIT_STYLE_FILE`), its first ~2,500 characters are injected into the
commit-plan prompt as **house commit conventions — authoritative for grouping
and message style**. Absent, empty, or unreadable means no section, never an
error.

This is the integration point for externally curated knowledge — a NotebookLM
briefing included. NotebookLM has no API and sits behind Google sign-in, so
the flow is export-based: in the notebook, have it produce the git-conventions
guide, export it (copy the note, or send to Docs and download as Markdown),
and save it as `docs/COMMIT-STYLE.md`. The next `pf commit` reads it
automatically. The guide informs the model's *judgment* only — grouping and
wording; every guardrail (validation wall, gate, provenance) is unchanged by
anything the file says.

## Session-end automation

`.claude/settings.json` carries a `Stop` hook running
`pf git-doctor --from-hook --apply` and then `pf commit --from-hook --auto`.
Both are **no-ops unless `PF_AUTO_COMMIT=1`** — armed, every Claude Code
session ends with the local model first repairing tree states (doctor), then
splitting and committing whatever the session changed (committer); unarmed,
nothing happens and both stay deliberate commands. The doctor runs first on
purpose: a drifted pin or stale plan would otherwise pollute the commit
survey it feeds.

## Guardrails, named

Two policies in `platform/src/pf/ontology/policy.yaml`, resolving under
`pf air coverage`:

- `commit-plans-are-validated-not-trusted` — the deterministic wall between
  the model's opinion and the index (`AIR-PREV-18`, `AIR-PREV-19`).
- `llm-commits-are-recorded-and-attributed` — provenance action per commit,
  model named in the message (`AIR-DET-21`, `AIR-DET-4`).

And two the committer inherits rather than implements: the pre-commit hook
still blocks a breaking change on every commit it makes, and the provenance
ledger's kill switch is honoured by construction — a revoked ledger refuses
the action record, and with it the commit.

Tests: `platform/tests/test_committer.py`.

## The git doctor

`pf git-doctor` extends the same division of labor from pending work to
*wrong states*: submodule checkouts off their recorded pin, nested submodules
initialized inside vendored checkouts, stale commit plans, conflicts,
gate-denied paths git tracks anyway. Deterministic scanners find them; the
local model's entire authority is choosing a remedy per finding from a
**closed menu** — it composes no command, ever.

The detailed rule is written down, not implied: `pf git-doctor --rules`
prints the rulebook (`pf.gitdoctor.RULEBOOK`), the exact text the model
receives. It enumerates the menu per finding kind, and the permanent
prohibitions no finding can unlock: pin bumps, history rewrites (`reset
--hard`, rebase, force-push, amend), gate bypasses (`--no-verify`), edits
under `vendor/**` or `.gitmodules`, anything in `provenance/**` or `.git/`,
and merge resolution. The only answer for those is `leave`, which hands the
finding to a human with a stated reason — findings the model omits default to
`leave` too.

```bash
pf git-doctor            # diagnose + the model's proposed resolutions
pf git-doctor --apply    # run the accepted remedies (each a provenance action)
pf git-doctor --rules    # print the rulebook and exit
```

An off-menu resolution is rejected before anything runs
(`git-repair-is-a-closed-menu` in `policy.yaml`, resolving under
`pf air coverage`). Tests: `platform/tests/test_gitdoctor.py`.

## The import-cycle guard

The circular-import invariant is held twice, at different hardnesses:

- **The wall** — `platform/tests/test_import_cycle_guard.py` walks the real
  module-level imports of `platform/src/pf` and fails the suite (and the
  merge, since `pytest platform/tests` gates it) on any cross-module cycle.
  Function-scope imports and the parent-package re-export idiom are exempt —
  they are the sanctioned ways to break a cycle, not instances of one.
- **The doctor's eye** — when `graphify-out/graph.json` exists, `pf
  git-doctor` reports `import-cycle` findings from the knowledge graph's
  directed `imports` edges (capped at 10, `calls` recursion ignored). It is
  `leave`-only: breaking a cycle is authorship, so the model names the knot
  and hands it to a human.

There is deliberately no hand-written PR workflow for this: `.github/
workflows/**` is gate-denied to agents and generated per project from
capability `ci_jobs` — the pytest wall rides the existing platform test job,
which is the same enforcement with none of the drift.
