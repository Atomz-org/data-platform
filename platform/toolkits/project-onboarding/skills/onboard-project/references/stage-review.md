# Stage 6 — Recce

**Goal condition:** the difference between what was there and what is there now
has been looked at.

Every stage before this one changed models: SQL was wrapped, directories were
moved, configs were re-keyed. All of it was supposed to be behaviour-preserving.
Lineage says what *could* break. Only a diff says what *did*.

This is the stage that catches the ambiguous-function class from the dialect
stage. `sf_least` compiles, `dbt parse` passes, `dbt build` succeeds, and one
column comes out different because the original really did rely on DuckDB's
NULL-skipping. Nothing before this point can see that.

## The two states

Recce compares two *built* states. The platform gives you somewhere to build the
second one: the `base` target writes the same DuckDB file under a `base` schema,
so both are reachable from one connection and the seeds load once.

```bash
cd groups/<g>/projects/<p>

# base — the state before this onboarding touched anything
git stash                                    # or: git worktree add ../base <ref>
DBT_TARGET=base dbt build --project-dir transform --profiles-dir transform \
  --target-path transform/target-base
git stash pop

# current
DBT_TARGET=dev dbt build --project-dir transform --profiles-dir transform
```

A worktree is cleaner than a stash for anything long: it keeps the base build
from colliding with edits in progress.

## Evaluate

```bash
pf align evaluate <group> <project> --stage review
```

- **`no-base-manifest` / `no-current-manifest`** — one of the two states does not
  exist yet.
- **`node-set-changed`** — models added or removed since base. Expected during an
  onboarding, but every *removal* is a model something downstream may still
  reference. Check each against `pf impact <group> <project> model:<name>` before
  accepting it.
- **`recce-absent`** — without the CLI this stage can confirm the two states
  exist and nothing about whether they agree.

## Implement

```bash
recce server                    # interactive: lineage, row-count and value diffs
recce run                       # headless, writes recce_state.json
```

What to actually look at, in order:

1. **Row counts** on every mart. A change of ±0 rows across a refactor is the
   expected result; anything else is either a real find or a seed that loaded
   differently between the two builds.
2. **Value diffs** on the models whose SQL you wrapped in stage 3. These are the
   highest-yield checks in the whole ladder — go straight to the models that
   used `least`, `greatest`, `datediff` or `date_trunc`.
3. **Schema diffs** where you moved a model between layers, since the schema name
   changes with the layer and downstream `ref()`s resolve differently.

Record the outcome in `decisions/`: which models you diffed, what changed, and
why each change is acceptable. A diff nobody wrote up is a diff nobody looked at
three months from now.

## Validate

```bash
pf align validate <group> <project> --stage review
```

Conditions: both states built, and `recce run` completing with no failed check.
It reports **unexercised** when recce is not installed (`uv add recce`).

## Then

Onboarding is over; cadence begins.

```bash
pf seed <group> <project>        # full build, then rebuild graph + card
pf loop run-all <group> <project>
pf align status <group> <project> --state
```

The project joins the scheduled loops in `LOOP.md` — freshness, test-failure
triage, metric-gap harvesting, PII audit — which is where discovery and triage
happen from here on. The one-off ladder does not run again unless something
regresses, and `pf align status` will say so when it does.
