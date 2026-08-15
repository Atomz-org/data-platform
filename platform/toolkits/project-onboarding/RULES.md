# project-onboarding — rules

Adopting a repository and aligning it with this platform, as a gated ladder:
`import → ontology → dialect → layers → metrics → review`. The skill is
`onboard-project`; the machinery is `pf align`.

- The order is a dependency, not a preference. Each stage consumes what the one
  before it produced, and a stage run early is a stage run twice.
- Evaluate and validate are code and cost nothing. Implement is the only phase
  that is an agent's, and it addresses **one** finding per iteration.
- Maker and checker are different questions. `pf align validate` asks whether the
  project is correct; `pf align verify` asks whether the change that got it there
  is acceptable. Both must pass, and they must not be the same agent.
- Three consecutive failures of a stage open a circuit breaker recorded in
  `loop-ledger.json`. Stop and escalate; do not attempt a fourth time and do not
  clear the breaker to keep going.
- `unexercised` is not a pass. It is what a check reports when the tool that
  would decide it is not installed, and reporting it as green is the difference
  between an onboarding that was verified and one that was assumed.
- A `decide` finding resolved without a note in `decisions/` is comprehension
  debt. The checker enforces this; do not route around it by grading findings
  down.
- Never `--force` past a blocker except for findings that are a later stage's
  work, and never to make a gate go green.
