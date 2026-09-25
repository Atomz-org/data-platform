# Evals for requirement-pipeline

There are no agent cases here yet, and that is deliberate.

A case under a toolkit's `evals/` drives one **agent step**: `pf.agents.base`
routes it, `pf evals` calls it, and the `expect` block is graded against what
the model returned. `build-from-requirement` ships no agent step. The
interactive agent does the extraction from Confluence into `spec.yaml`, and the
spec is then judged deterministically by `scripts/validate_spec.py`. A case
written against an agent that does not exist would pass by finding nothing.

What proves this skill is `platform/tests/capabilities/test_requirement_pipeline_skill.py`:

- every `pf` command the skill and its references name resolves in the CLI
- every skill, review agent and command it routes a phase to is shipped, in
  `SKILL.md`, `references/skill-map.md` and the validator's `SKILLS` table
- every toolkit skill has a place in the map, either routed to or handed back as
  out of scope, so a new toolkit skill fails until someone places it
- routing follows the spec's content: source kind, rule test type, foreign-dialect
  SQL, and a diff review only when something existing is modified
- its phase numbers agree with the validator's phase plan
- the validator refuses each class of spec the reference says it refuses
  (key and currency roles, layer naming, ungrounded metrics, averaged ratios,
  untested rules, inline credentials, no acceptance criteria), and plans
  `reuse` for what a project already has
- the Confluence converter keeps tables, code macros, panels and nested lists

If extraction is ever routed through a model, for example a `requirement_extractor`
agent that drafts `spec.yaml` from a snapshot, its cases belong here. Grade them
with the validator's exit code plus pinned fields: grain, metric type, the
layer of each rule.
