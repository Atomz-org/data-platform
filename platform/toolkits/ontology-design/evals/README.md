# Evals for ontology-design

There are no agent cases here, and that is a statement rather than an omission.

A case under a toolkit's `evals/` drives one **agent step** — `pf.agents.base`
routes it, `pf evals` calls it, and the `expect` block is graded against what
the model returned. `ontology-design` ships no agent step: the vocabulary is
designed by a person and an interactive agent together, and induction
(`pf semantic scan`) is deterministic — `pf.ontology.induct` makes no model
call. A case written against an agent that does not exist would be a green tick
for "found nothing", which is what every gate in this repository refuses to
give.

What proves this skill is `platform/tests/ontology/test_design_skill.py`: every
`pf` command the skill tells an agent to run resolves in the CLI, every path it
names exists, and the three ontology tiers it promises are the three that
`pf tool okf build` actually writes. A skill that has gone stale fails there.

If an ontology step is ever routed through a model — a proposer that drafts
extension axioms from a scan, say — its cases belong in this directory, beside
the skill that describes the work.
