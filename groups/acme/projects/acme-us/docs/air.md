# AI risk controls — acme-us

This project declares which AI controls it commits to in `air.yaml`, and
`pf air gate acme acme-us` blocks the merge when one of them is not
enforced. Controls come from whichever catalogues are registered —
`pf air catalogues` lists them and where each is checked out.

| command | what it answers |
| --- | --- |
| `pf air catalogues` | which control catalogues are registered |
| `pf air controls` | which controls exist |
| `pf air show <id>` | one control, and every regulation it discharges |
| `pf air baseline acme acme-us --suggest` | the controls that already pass |
| `pf air coverage acme acme-us` | which of them this project enforces |
| `pf air gaps` | only the ones it does not |
| `pf air crosswalk eu-ai-act` | the regulator's view of the same facts |
| `pf air register acme acme-us` | regenerate `governance/air-register.md` |

## Declaring a baseline

`air.yaml` is hand-written and carries the judgement:

- `baseline:` — controls this project commits to. These **block the merge**.
- `accepted:` — controls consciously not taken. `reason` and `owner` are both
  required, because an acceptance without them is a gap with better formatting.
- `profile:` — where this project sits in the framework's taxonomy.

A project may add to its group's baseline; it cannot remove from it. The way to
drop a control is `accepted:`, which leaves a name attached to the decision.

## The register is generated

`governance/air-register.md` is derived from `air.yaml` plus a fresh coverage
run and is on the gate denylist — hand-editing it would make it disagree with
the declaration it came from. Change `air.yaml`, then `pf air register`.

It carries the credit line of every catalogue it drew from, collected from the
sources actually loaded rather than templated — so a catalogue swapped out takes
its obligation with it, and one added brings its own.
