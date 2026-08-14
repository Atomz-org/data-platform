---
when: Upgrading dbt Core, migrating to Fusion, or retargeting the warehouse. One-time operations.
rules:
  - These change every project in the repository — never run one while working on a single company.
---

# dbt-migrate

Migrations are platform operations, not project work. Running one from inside a
project session changes shared infrastructure on behalf of every other company in
the repository.
