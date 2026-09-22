---
type: Concept
title: Employee
description: Internal actor. Rarely modelled in marts; used for attribution.
okf_x_tier: group
okf_x_parent: Party
okf_x_abstract: false
okf_x_identity: employee_id
okf_x_platform_concept: ../../../../platform/okf/concepts/Employee.md
---

Extends the platform's [Employee](../../../../platform/okf/concepts/Employee.md); this page is what this family added.

# Properties

| Property | Datatype | Role |
|---|---|---|
| `department_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `employee_id` | string | [natural_key](/roles/natural_key.md) |
| `hire_date` | date | [event_time](/roles/event_time.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `position_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `store_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `termination_date` | date | [event_time](/roles/event_time.md) |
