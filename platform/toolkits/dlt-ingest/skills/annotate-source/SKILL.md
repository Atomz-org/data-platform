---
name: annotate-source
description: Attach ontology meaning to a dlt resource. Use after scaffolding a source and before writing any dbt model.
---
# Annotate a source

This is the platform's canonical data model step. Annotations drive staging
generation, PII policy, monitors, metric candidates and graph edges.

```python
@dlt.resource(name="charges", write_disposition="merge", primary_key="id")
@annotate(
    concept="Payment",                       # must be concrete; see ontology_classes
    grain="one payment attempt",
    description="Stripe charge events",
    roles={"id": "natural_key", "amount": "money_amount",
           "currency": "currency_code", "created": "event_time",
           "status": "status_enum", "receipt_email": "pii_email"},
    links={"customer_id": "Customer", "subscription_id": "Subscription"},
)
def charges(client): ...
```

Rules enforced by `validate_annotations`:
- concept exists and is not abstract
- every role exists in the ontology
- every `links` target is a legal topology edge
- every `money_amount` has a sibling `currency_code`
- exactly one key column

Run `validate_annotations` before moving on. Do not "fix" a failure by removing
the annotation.
