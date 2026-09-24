# `gates` — does the platform still hold together?

**Workflow:** `.github/workflows/platform.yml` · **Job:** `gates`

## In one paragraph

Four commands, each asking a question no single file owns. Are the instruction
files every AI session loads still small enough to afford? Does the shared
business vocabulary still hold together? Is every company fully set up? Is each
family governed enough to be trusted with more automation? **Any one failing
blocks the merge.**

## The four checks

| Step | Command | Fails when |
|---|---|---|
| Always-on context budget | `pf tokens` | **Any one file exceeds its budget.** `over = over or n > BUDGET` |
| Ontology conformance and blast radius | `pf check` | *See the caveat below* |
| Every family is onboarded | `pf group verify` | Any `active` or `suspended` group has a failing check |
| Per-family loop readiness | `pf loop audit --per-group` | The **lowest** group score is below 55 |

## Worked example — the context budget

You add a shared toolkit under `platform/toolkits/` and, so agents know it
exists, add a two-line bullet to the root `CLAUDE.md`.

```
platform | CLAUDE.md | 712 | 700 | OVER
```

The job exits 1.

**Why.** `CLAUDE.md` is the router every agent session loads before doing
anything. It is capped at **700 tokens** (`ROUTER_BUDGET`,
`platform/src/pf/kg/card.py:26`) because every session pays for it, forever.
At the time of writing it sits at **699 of 700** — one token of headroom.

**Fix.** Do not raise the budget. The router is an index, not documentation:
put the description in the toolkit's own `SKILL.md` and leave one line in the
router pointing at it.

```bash
uv run pf tokens     # shows every file, its estimate and its budget
```

## Two checks that print red but cannot fail the job

This is worth knowing before you spend an hour on the wrong line.

In `pf check`, the **pre-commit/pre-push hook status** is printed with a red ✗
(`cli.py:1316-1326`) but is never folded into the `failed` flag that decides
the exit code (`cli.py:1335`). A red hook row in the log is a diagnostic, not
the cause of the failure. Keep reading for the check that actually exited 1.

## Reproduce locally

```bash
uv run pf check
uv run pf tokens
uv run pf group verify
uv run pf loop audit --per-group
```

Each is the same command CI runs, with the same exit code.

## Why a token budget is a merge gate at all

It looks like housekeeping. It is not. Every agent session in this repository
loads the router before it can do anything, so a paragraph added there is paid
for by every session, on every task, indefinitely. Unbudgeted, the file grows
by one reasonable-looking paragraph at a time until the context it was meant to
save is the context it consumes.

The budget makes that cost visible at the moment someone adds to it, which is
the only moment anyone is in a position to decide it is worth paying.
