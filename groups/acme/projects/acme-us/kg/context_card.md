## acme-us — data index (generated 2026-08-12)

**Group:** acme · **Concepts in use:** Customer, Payment, Subscription
**Sources (1):** stripe

**Raw tables (3):**
- `charges` → Payment — one payment attempt
- `customers` → Customer — one customer account
- `subscriptions` → Subscription — one subscription

**Staging models (3):** `stg_stripe__charges`, `stg_stripe__customers`, `stg_stripe__subscriptions`

**Marts (3):**
- `dim_customers` — grain: one customer — Customer dimension with subscription rollups.
- `fct_payments` — grain: one payment attempt — Payment fact at attempt grain, enriched with customer and plan.
- `fct_revenue` — grain: one day x segment x plan — Daily revenue by segment and plan. Union-compatible across sisters.

**Metrics (6):**
- `active_customers` (simple) — Active Customers
- `aov` (ratio) — Average Order Value
- `gross_payment_volume` (simple) — Gross Payment Volume
- `payment_count` (simple) — Payments
- `revenue` (simple) — Revenue
- `revenue_mom_growth` (derived) — Revenue MoM Growth

**Common dimensions:** country_code, created_at, customer_segment, paid_at, payment_status, plan_tier

**Exposures (2):**
- `crm_customer_sync` (application) ← RevOps
- `exec_weekly_dashboard` (dashboard) ← Finance

**PII columns (6):** charges.receipt_email, customers.email, customers.name, stg_stripe__charges.receipt_email, stg_stripe__customers.customer_email, stg_stripe__customers.customer_name

**Known gaps:**
- 3 raw table(s) have no metric coverage

_Query the graph before reading files: `kg_search`, `kg_neighbors`, `kg_path`._
