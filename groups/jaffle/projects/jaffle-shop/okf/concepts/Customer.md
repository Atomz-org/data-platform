---
type: Concept
title: Customer
description: A party that buys. May be a person or an organization.
okf_x_defined_in: platform
okf_x_parent: Party
okf_x_identity: customer_id
okf_x_kg_node: concept:Customer
okf_x_platform_concept: ../../../../../../platform/okf/concepts/Customer.md
---

Defined by the platform ontology: [Customer](../../../../../../platform/okf/concepts/Customer.md).

# Instantiated by

* [customers](/tables/customers.md)
* [dim_customer_360](/tables/dim_customer_360.md)
* [ml_feature_customer_churn](/tables/ml_feature_customer_churn.md)
* [rev_etl_crm_customer_sync](/tables/rev_etl_crm_customer_sync.md)
* [rev_etl_email_segment_at_risk](/tables/rev_etl_email_segment_at_risk.md)
* [rev_etl_email_segment_high_value](/tables/rev_etl_email_segment_high_value.md)
* [scr_customer_churn_propensity](/tables/scr_customer_churn_propensity.md)

# Properties

| Property | Datatype | Role |
|---|---|---|
| `country` | string | geo_country |
| `created_at` | timestamp | event_time |
| `customer_id` | string | natural_key |
| `email` | string | pii_email |
| `id` | string | natural_key |
| `name` | string | pii_name |
| `segment` | string | status_enum |

# Relations

* Customer belongs to Organization — A customer may sit under a parent organization.
* Customer holds Subscription — The spine of any recurring-revenue model.
* Customer located in Location — 
* Customer participates in Interaction — 
* Customer pays Payment — 
* Customer places Order — 

# Raw tables that instantiate it

* `jaffle-seeds.raw_customers`

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
