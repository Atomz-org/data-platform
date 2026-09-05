# Ontology segregation — test plan

How we prove the three ontology layers stay separate, and how to run that
proof locally before a commit. The suite is
`platform/tests/test_ontology_segregation.py`; the mechanism under test is
`pf.ontology.model` (loading and merging) and `pf.ontology.validate`
(conformance). `docs/SEMANTICS.md` describes the layers themselves.

## The contract under test

| Layer | File | May contain | May never contain |
|---|---|---|---|
| platform | `platform/src/pf/ontology/{concepts,topology,policy}.yaml` | universal vocabulary, all policy | any group-invented term |
| group | `groups/<g>/ontology/extension.yaml` | the group's own classes/roles/relations; property additions to platform classes | policy; a re-parented platform class |
| group | `groups/<g>/ontology/instance.yaml` | a *selection* of platform classes | definitions of any kind; extension terms |
| project | `<project>/contracts/annotations.yaml` | bindings of physical columns to platform+group vocabulary | terms from any other group |

## Aspects covered, by leak direction

**Upward — group terms leaking into the base**
- No class is defined by both the platform ontology and a group extension
  (shadowing to add properties is the supported exception).
- The platform base is internally coherent on its own (`validate_topology`).
- Loading every group's merged ontology leaves the lru-cached base
  untouched — the cache-contamination path that no YAML review would catch.

**Sideways — vocabulary transferring between sisters**
- Classes a group invented are invisible from every other group's merged
  ontology; likewise group relations. Pairwise, over every group discovered
  under `groups/*/ontology/` — a new group is covered automatically.
- mental-health's *real* annotations, validated under each sister group's
  ontology, fail `unknown-class` for every hospital-bound resource. If that
  test ever passes under a sister, hospital vocabulary has leaked.

**Downward — the merge damaging what it layers over**
- An extension adds classes/roles/relations without dropping anything from
  the base; property additions keep the platform class's parent, identity
  and own properties intact.
- A relation restated by a group replaces exactly one relation, by name.
- No real extension re-parents a platform class (identity rebinding is an
  accepted pattern; re-parenting rewrites the shared hierarchy and is not).
- `policies:` in an extension is ignored — governance does not federate.
- Every real merged group ontology is itself coherent (`validate_topology`).

**Selection — instance.yaml speaks platform only**
- Every real `groups/*/ontology/instance.yaml` passes `validate_instance`.
- An instance naming an extension class (`Patient`) fails, even though the
  class is real for that group — the instance layer selects, never defines.
- A missing instance is reported, not silently passed.

**Project — bound to its own group's vocabulary, and only that**
- The validating ontology is derived from the project's path
  (`groups/<g>/projects/<p>`), never passed as a parameter; paths outside
  that shape, or naming no real group, fall back to the bare platform.
- The live mental-health project validates with zero errors against
  platform+hospital.
- The bare platform rejects group concepts; the owning group accepts them.
- A role a group marks PII is honoured through the group ontology
  (`review_intent == "none"`, listed by `pii_columns`) and does not exist
  at all outside it — validating with the wrong layer would drop the flag.

## Running it locally, before commit

```sh
# the segregation suite alone (~1s, no warehouse needed)
uv run pytest platform/tests/test_ontology_segregation.py -q

# with the sibling governance suite (proposal/approval flow)
uv run pytest platform/tests/test_ontology_segregation.py \
              platform/tests/test_ontology_governance.py -q
```

The pre-commit hook (`platform/hooks/pre_commit.sh`) runs the suite
automatically whenever a staged path touches `platform/src/pf/ontology/`,
any `groups/*/ontology/`, or a project's `contracts/annotations.yaml`, then
proceeds to `pf gate` as before. A failure blocks the commit; bypassing with
`--no-verify` follows the usual rule — say why in the message.

## Extending the suite

- **New group**: nothing to do — groups are discovered by globbing
  `groups/*/ontology/`. Give it an `instance.yaml` and it is covered.
- **New project**: add its directory to a `validate_project` test if it
  should be pinned like mental-health; path-derivation and cross-group
  checks already apply.
- **New layer rule**: put loader/merge semantics in the group-level section,
  conformance rules in the direction they guard against, and always test
  both the accepting layer and the rejecting one.
