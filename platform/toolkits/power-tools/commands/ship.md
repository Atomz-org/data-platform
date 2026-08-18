---
name: ship
description: Take the current change from working tree to a reviewable commit — gate, conformance, blast radius, data diff, then one conventional commit.
disable-model-invocation: "yes"
---

# Ship

Ordered. Each step produces the input for the next; a failure stops the sequence
rather than being noted and passed over. `$ARGUMENTS` may carry a commit subject.

## 1. See what is actually changing

```bash
git status --short
git diff --stat
```

If the change spans more than one concern, stop and split it. A commit that does
two things cannot be reverted for one of them.

## 2. Gate

```bash
uv run pf gate --paths "$(git diff --name-only HEAD | tr '\n' ',')"
```

A denied path is not a thing to argue with. Either the file is generated (then
regenerate it properly) or the rule is wrong (then change `gate.yaml`
deliberately, in its own commit, with the reason in the comment beside it).

## 3. Conformance and reach

```bash
uv run pf check
```

Ontology conformance plus the blast radius of everything modified. Undeclared
joins fail here. If the reach includes metrics or a published contract
(`mdl/mdl.json`, `catalog/openmetadata.json`), say so in the commit body — that
is what makes the change reviewable rather than merely correct.

## 4. Build and test what you touched

```bash
uv run dbt build --select state:modified+ --defer --state transform/target-base
```

Falling back to `dbt build --select <the models> ` when no base state exists.
Tests are part of this step, not a later one.

## 5. Data diff, when models changed

```bash
uv run pf tool recce run <group> <project>
```

Read `transform/recce_summary.md`. Numbers that moved unexpectedly are a finding,
not a formality — resolve before committing, and reference the summary in the
commit body when they moved for a good reason.

## 6. Commit

Conventional commit. Subject in the imperative, under ~70 characters, saying what
changed and for whom. Body: why, and the blast radius if it was non-trivial.

```bash
git add <the specific paths>        # never `git add -A`
git commit
```

The pre-commit hook re-runs the gate over the staged set. If it blocks, it is
right; fix rather than bypass. `--no-verify` is not part of this workflow.

## 7. Stop

Do **not** push and do **not** open a PR unless that was explicitly asked for.
Report: what was committed, what the blast radius was, what recce said, and what
remains. Pushing is the user's call — the branch is theirs to place.
