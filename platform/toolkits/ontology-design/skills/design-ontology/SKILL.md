---
name: design-ontology
description: Design or extend the business vocabulary — classes, their identity, properties with roles, and named relations — and publish it through all three tiers. Use before annotating a source or writing a mart for a domain the ontology does not describe yet.
---
# Designing the ontology

The vocabulary is written before the models, not after. Every downstream thing
— generated staging, PII masking, MDL joins, metric grain, the OKF bundles an
agent reads — is derived from it, so a class invented in a mart is a term
nothing enforces and a term nobody else can use.

`steward-ontology` is the sibling skill: it reviews what a **scan proposed**.
This one is for the part where nothing has been proposed yet — a new domain, a
new family, a concept the business names and the platform has no word for.

```
pf ontology                                  # what the platform already means
pf semantic topology                         # the relations that already exist
pf semantic scan <group> <project> --source <name>   # evidence, if a source has landed
<edit groups/<group>/ontology/extension.yaml>        # the actual work
pf check                                     # conformance, before anything is built on it
```

## First: which tier

Three layers, and putting a term in the wrong one is the expensive mistake.

| Tier | File | Put a term here when |
|---|---|---|
| platform | `platform/src/pf/ontology/concepts.yaml` | every company would recognise it — `Customer`, `Payment`, `Event` |
| group | `groups/<group>/ontology/extension.yaml` | this family's business needs it — `ImportTariff`, `PriceObservation` |
| project | `contracts/annotations.yaml` | it is a physical binding, not a word — this table is that class |

A class one company invented does not go in the platform ontology: every other
company then inherits a term that means nothing to them, and the rollup gets a
column it cannot fill. Promotion from group to platform is a separate,
deliberate edit — make it when a **second** family needs the same word.

## The six decisions

**1. One class per thing the business names.** Not one per table. Several
tables at different grains are usually one entity: `orders`, `order_events`
and `order_snapshots` are `Order`. Use the word the business uses in the
meeting, not the word the source system chose — `Charge` is Stripe's name for
a `Payment`, and minting the synonym splits every metric built on it.

**2. Identity is a decision, not a column.** Each class declares one
`identity` property: the thing that says two rows are the same thing. It is
what every derived join targets, so it is chosen, not discovered — the scan
sees the source's key and the ontology holds the modelled name someone chose.
When the same entity arrives from two systems, decide **before** writing the
class how they reconcile: which source wins per attribute, and whether a row
present in only one source is still the entity. Record that decision where it
will be read — an ADR in `decisions/`, not a comment.

**3. Properties carry a role, and the role carries the policy.** Declare
`{datatype, role, required}` per property. The role is not decoration: it
drives generated staging, currency normalisation, PII masking, the monitors,
the MDL type and the OKF definition. `pf ontology` lists the roles that exist
— reuse one before inventing one, and invent one only when an existing role
would be the wrong *contract* (this family's `unit_price` exists because
`money_amount` is additive and a price is not).

**4. Relations are named with a business verb.** `customer_pays_payment`, not
`customer_refers_to_payment`. Each declares `domain`, `range`, `cardinality`
and the `inverse` phrase a reader sees in the reverse direction. This is what
becomes an MDL join and a lineage edge — a relation named `refers_to` is a
placeholder, and a join derived from a placeholder is a guess.

**5. No property without a column, and no class without a source.** If a use
case needs something the data cannot answer, that is a **gap**: write it down
as a gap — an ADR, or a proposal left unapproved — and say where the data
would come from. Do not model the wish. A class with no table to instantiate
it reaches the bundle as a concept nothing documents, and reads as a mistake
rather than as a decision.

**6. PII is declared, never inferred.** A role marked `pii: true` masks the
column everywhere downstream. A wrong tag carries authority it did not earn; a
missing one fails the mart policy loudly, which is the safer failure.

## Publishing it

Approval is what makes a term real, and it propagates:

```
pf semantic approve <group> <id> --by <you>   # induced terms; hand edits need no approval
pf kg build <group> <project>                 # the term becomes a node
pf semantic mdl <group> <project>             # and a join, where a relation binds a column
pf tool okf build --all --platform --group    # and a page in all three bundles
```

Every tier has a bundle: `platform/okf/` for the shared vocabulary,
`groups/<g>/okf/` for what this family added, and each project's `okf/` for
the tables that instantiate it. A concept page in a project links up to the
family's; the family's links up to the platform's. That chain is how an agent
gets from a column it is reading to the definition every sister shares.

## Before you call it done

```
pf check                          # conformance: every class reachable, every policy enforced
pf semantic topology              # read the relations back as sentences
pf semantic mdl --check --all     # the manifest agrees with the graph
pf tool okf check --all           # every bundle agrees with the ontology
pf air coverage                   # the controls a new PII role just implicated
```

A term that is in the YAML and in none of the above is not published; it is
just written down.
