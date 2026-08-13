---
name: steward-ontology
description: Review and approve an induced ontology proposal after scanning a new data source. Use whenever a source has landed and its concepts are not yet in the vocabulary, or when asked to model, curate or approve terms.
---
# Stewarding an induced ontology

Scanning a source proposes vocabulary. It does not decide it. Your job is the
part induction cannot do: deciding what a thing **means**.

```
pf semantic scan    <group> <project> --source <name>
pf semantic review  <group> <id>            # and --show rejected
<edit the YAML>                             # this is the actual work
pf semantic approve <group> <id> --by <you>
```

## The four judgements induction cannot make

1. **Is this an existing concept under a new name?** A scan of Stripe proposes a
   class `Charge`. That is Stripe's word for a `Payment`. Reject the new class and
   remap its properties onto the existing one. Minting a synonym splits every
   downstream metric, and nothing will tell you it happened.
2. **What is the business verb?** Induced relations are named
   `x_refers_to_y` — a placeholder that tells a reader nothing. Rename it:
   `customer_pays_payment`, `subscription_settles_payment`. Relations are never
   pre-accepted for exactly this reason.
3. **Is this really personal data?** PII is proposed, never pre-accepted, at any
   confidence. A wrong tag carries authority it did not earn; a missing one fails
   the mart policy loudly, which is the safer failure.
4. **Does it specialise something?** Set `parent` where a class is a kind of an
   existing one. Inheritance is what lets a policy written for `Event` reach a
   concept invented later.

## Things that should make you reject

- An identity axiom on a class that already has one. The scan sees the raw source
  column; the ontology holds the modelled name someone chose. Accepting it
  replaces a decision with an accident, and every derived join follows the wrong
  column. The tooling now withholds these — do not override without a reason.
- A class per table when several tables are one entity at different grains.
- `free_text` on something that is really a dimension, or vice versa. Check the
  distinct count in the evidence, not the column name.

## Where approved terms go

`groups/<group>/ontology/extension.yaml` — this group only. Another company never
inherits a word that means nothing to them. Promoting a term to the platform
ontology is a separate, deliberate edit.

Approval propagates automatically to the knowledge graph, the MDL manifest and
the reporting layer of every project in the group. An approved term that has not
reached the graph is not usable by dbt, Wren, BI or an agent.
