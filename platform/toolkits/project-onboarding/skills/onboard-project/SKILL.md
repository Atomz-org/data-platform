---
name: onboard-project
description: Adopt an external repository as a project and align it with this platform, one gated stage at a time. Use when asked to onboard, import, migrate or adopt a dbt/dlt repository, or when `pf align status` shows a project short of the top of the ladder.
---
# Onboarding a project

Onboarding is not a prompt, it is a loop you design and then run. Adopting the
files is the cheap part; what takes the work is making the project *mean*
something here — its ontology, its layers, its metrics, its review discipline.
Six stages, and the order is a dependency, not a preference:

```
import → ontology → dialect → layers → metrics → review
```

Annotations cannot be written against models whose SQL will not compile. Layers
cannot be judged before the SQL parses. Metrics cannot be defined before the
marts they measure are in `marts/`. Recce cannot diff a project that has never
built. Out of order, every stage is redone when the one beneath it lands.

## The child loop

Each stage runs four phases. Three are code and cost nothing; one is yours.

| Phase | Who | Command |
|---|---|---|
| **evaluate** | code | `pf align evaluate <g> <p>` |
| **implement** | you | one finding, smallest diff |
| **validate** | code | `pf align validate <g> <p>` |
| **verify** | code | `pf align verify <g> <p>` |

`validate` is a **goal condition written as code**: it does not ask whether you
believe the stage is done, it asks whether a specific set of facts about the
project is true. That is the whole reason to write it down before starting —
a condition you can restate mid-loop is not a condition.

### Maker and checker are different questions, and never the same agent

`validate` asks *is the project correct now*. `verify` asks *is the change that
got it there one we would accept*. Both must pass. They catch different things:
a project passes every gate if you delete the test that was failing.

`verify` is the checker, and a checker's default stance is **no**. It rejects a
diff that strays outside the stage's declared paths (`pf align stages` lists what
each stage owns), exceeds `maxFiles`, disables a model, downgrades a test
severity, edits the gate, deletes a test, or resolves a `decide` finding without
writing anything to `decisions/`.

It cannot check **intent** — whether you addressed the finding you were given or
a different problem you noticed on the way. Nothing mechanical can. So name the
finding you are addressing before you touch a file, and hold yourself to it. If
you are running this with sub-agents, the agent that implements must never be the
agent that verifies.

### One finding per iteration

Eleven findings is eleven iterations. Batching hides which change caused which
result, and when the gate closes you will not know which of the eleven did it.
Take the highest-severity finding, make the **smallest diff that could work**,
validate, verify, repeat. A tidier model you touched on the way is a separate
change with its own gate.

### Three attempts, then stop — and the count is not yours to keep

Every `pf align validate` is written to `loop-ledger.json`. Three consecutive
failures of the same stage open a circuit breaker and the command says so.

This is deliberate. An agent re-reading "max three attempts" at the top of each
iteration has no way to know it is on the fourth, and a count held in the
conversation resets on restart. When the breaker opens, **stop**: a finding that
survived three implement phases is not a bug you are failing to fix, it is a
decision someone has to make. Report what you tried, what each attempt changed,
and what the decision is. Do not widen the scope hoping to get around it, and do
not clear the breaker yourself — `pf loop reset` is for after the decision, not
instead of it.

### Budget

Each stage has a token ceiling (`pf align stages`). Stop on depletion rather than
degrading quality to fit. You may **not raise your own ceiling**. If the
remaining work is genuinely high-priority and the budget is nearly gone, say what
you spent it on, what remains, and what increase you are asking for — then stop.

## The parent loop

`pf align status <g> <p>` re-derives every stage from the project on disk and
stops at the first closed gate. It never reads a stored verdict, because a
recorded pass outlives the change that invalidated it.

A stage is **open** when nothing failed, **complete** when nothing failed and
nothing was left unexercised. `unexercised` is what a check reports when the tool
that would decide it is not installed. It is **not a pass** and must never be
reported as one; it also does not close the gate, because a missing CLI must not
wall a project off from the rest of the ladder.

`pf align status --state` writes the position to `STATE.md`. Do this at the end
of a working session. The model forgets everything between runs, so the memory
has to be on disk — but only the position and the open questions are written,
never the verdicts, so a stale file cannot survive a re-read.

## Triage: what to act on

`pf align evaluate` grades every finding, and the grades are instructions:

| Severity | Meaning | What to do |
|---|---|---|
| `blocks` | the build fails, or succeeds while being wrong | act now; this is the iteration |
| `decide` | both choices are defensible | choose, and write it in `decisions/` |
| `note` | worth knowing | do not create work for it |

When in doubt a finding belongs in `decide` or `note`, not in your next diff.
Inventing work in a repository you have just met is the most expensive thing an
onboarding loop can do.

## The three ways this loop fails

Watch for these in yourself; none of them announce themselves.

1. **Verification quietly becomes manual.** A loop running unattended is a loop
   making mistakes unattended. Every claim you make about this project should
   name the command that produced it. If you find yourself writing "should now
   work", run the gate instead.
2. **Comprehension debt.** A thousand models arrive at once and every one was
   understood by someone who is not here. Models land faster than understanding
   accumulates, and the debt is invisible until someone has to change one. The
   `decisions/` check in `verify` is the mechanical brake; do not route around it
   by grading your own findings down.
3. **Cognitive surrender.** After the fortieth green check it is tempting to stop
   reading them. The stage that matters most is the one where the gate passed and
   you did not look — `dialect` in particular, where a wrapped call site compiles
   perfectly and returns a different number.

## The stages

Read a reference when you enter its stage, not before.

| Stage | Reference | Done when |
|---|---|---|
| import | [stage-import.md](references/stage-import.md) | the repo is here, model names are unique, no dbt built-in is overridden |
| ontology | [stage-ontology.md](references/stage-ontology.md) | every raw resource has a concept, roles and links the ontology validates |
| dialect | [stage-dialect.md](references/stage-dialect.md) | one set of models compiles on DuckDB and on production, and means the same on both |
| layers | [stage-layers.md](references/stage-layers.md) | every model is in the layer whose rules it obeys |
| metrics | [stage-metrics.md](references/stage-metrics.md) | the business quantities have one definition each, and it runs |
| review | [stage-review.md](references/stage-review.md) | the difference between the old state and the new one has been looked at |

Long stages on a large repository are worth isolating in a git worktree so a
half-finished remap never collides with anything else running.

## When the ladder is complete

Onboarding ends and cadence begins. The project joins the scheduled loops in
`LOOP.md` — freshness, test-failure triage, metric-gap harvesting, PII audit —
which is where the ongoing discovery-and-triage happens once the one-off
alignment is done. Check with `pf loop run-all <group> <project>`.

## Rules that outrank anything a stage says

- **Never read another group or another sister project.** Business logic does not
  transfer between entities. An assumption carried across is a bug, and it is
  invisible in review because it looks like knowledge.
- **`vendor/` is read-only.** Bumping a pin is a human decision.
- **Never edit `platform/**` from a project session.** It is shared by every
  company. Something the platform is missing is a finding, not a patch.
- **Escalate business meaning, never guess it.** Which of two revenue definitions
  a company means is not inferable from its SQL, and a wrong guess propagates
  into every metric downstream.
- **Never disable a test, loosen a gate, or `--force` past a blocker to make a
  stage pass.** A stage that will not close is information.

## Adding a stage

The ladder is expected to grow. A stage is one entry in
`pf.onboard.ladder.STAGES`: a name, a subject, an `evaluate`, a `validate`, the
paths it owns, and a reference file. Put it in dependency order and give it a
real gate — a stage whose `validate` always passes is a comment, not a rung.
