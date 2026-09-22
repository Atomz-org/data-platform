---
name: evidence-travels-with-features
description: Every new feature lands with the test or eval that proves it, in the same commit; gate.yaml tests_required enforces it (new source without evidence is refused, modified is warned); never make the suite green by deleting or loosening a check
type: feedback
status: active
agent: claude-code
---

**Why:** Set as a standing rule by the platform owner on 2026-09-22, when the
harness layer landed: every new feature ships with the evals that verify it,
so a change cannot pass by having nothing to fail and cannot break what
already works. Before this, a new module under `platform/src/pf/` or a new
skill with no eval case passed every check there was — the same hole
`pf group verify` closed for groups with no projects.

**How to apply:** The test or eval goes in the *same commit* as the code —
split work by feature, never "code now, tests next commit". `gate.yaml`
`tests_required` enforces it: a new file under `platform/src/pf/` or
`platform/hooks/` needs a path under `platform/tests/`; a new skill under a
toolkit needs a case under that toolkit's `evals/`; modifying one without
evidence warns. Deleted tests are not evidence (the gate never sees
deletions). Two things the gate cannot check are still the rule: the evidence
must fail before the change and pass after it, and the existing suite must
stay green untouched — never delete or loosen a check to make room. See
`AGENTS.md` §4 and §7.
