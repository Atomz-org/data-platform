---
type: Context Card
title: jaffle/jaffle-shop
description: Always-in-context index for jaffle/jaffle-shop.
tags:
- context-card
- jaffle
- jaffle-shop
status: stable
---

## jaffle-shop — data index

**Group:** jaffle · **Concepts in use:** AccountReceivable, Budget, Campaign, CampaignSpend, Coupon, CouponRedemption, Customer, DeliveryShipment, Department, EmailEvent, Employee, Equipment, Expense, ExpenseCategory, GiftCard, +42 more
**Sources (1):** jaffle-seeds

**Raw tables (57):**
- `raw_accounts_receivable` → AccountReceivable — one accountreceivable (8 rows scanned)
- `raw_budgets` → Budget — one budget (8 rows scanned)
- `raw_campaign_spend` → CampaignSpend — one campaignspend (10 rows scanned)
- `raw_campaigns` → Campaign — one campaign (7 rows scanned)
- `raw_coupon_redemptions` → CouponRedemption — one couponredemption (8 rows scanned)
- `raw_coupons` → Coupon — one coupon (7 rows scanned)
- `raw_customers` → Customer — one customer
- `raw_delivery_shipments` → DeliveryShipment — one deliveryshipment (7 rows scanned)
- `raw_departments` → Department — one department (6 rows scanned)
- `raw_email_events` → EmailEvent — one emailevent (10 rows scanned)
- `raw_employees` → Employee — one employee
- `raw_equipment` → Equipment — one equipment (8 rows scanned)
- …and 45 more (use `kg_search`)

**Staging models (58):** `stg_accounts_receivable`, `stg_budgets`, `stg_campaign_spend`, `stg_campaigns`, `stg_coupon_redemptions`, `stg_coupons`, `stg_customers`, `stg_delivery_shipments`, `stg_departments`, `stg_email_events`, `stg_employees`, `stg_equipment`, `stg_expense_categories`, `stg_expenses`, `stg_gift_cards`, +43 more

**Marts (996):**
- `adv_above_store_average` — Orders where the amount exceeds the store's average order total, identified using a correlated subquery in the WHERE clause.
- `adv_calendar_with_events` — Annotated business calendar joining util_date_spine with campaign dates and supplier contract dates via UNION ALL. Every calendar day shows active business events and their categories.
- `adv_category_hierarchy` — Full parent-child category hierarchy built using a recursive CTE over dim_menu_categories.
- `adv_conditional_aggregates` — Conditional aggregations using PostgreSQL's FILTER clause as a cleaner alternative to CASE WHEN inside aggregate functions.
- `adv_consecutive_growth` — Longest streaks of consecutive month-over-month revenue growth per store, detected using the islands-and-gaps technique with window functions.
- `adv_cumulative_with_reset` — Cumulative daily revenue that resets at the start of each fiscal quarter. Uses util_fiscal_periods for quarter boundaries and partitions the window by fiscal_year and fiscal_quarter.
- `adv_customer_analysis_cube` — All possible aggregation combinations of customer type, location, and order year using CUBE, producing 2^3 = 8 grouping levels including grand total.
- `adv_customer_health_matrix` — 27-segment customer health matrix crossing frequency (high/medium/low), recency (active/cooling/dormant), and monetary (high/medium/low) dimensions using complex nested CASE expressions over int_customer_rfm_scores.
- `adv_customer_order_pairs` — Each customer order paired with their previous order using LAG window function. Outputs days between orders, amount change percentage, whether the store changed, and whether the product mix changed.
- `adv_customer_product_array` — Each customer's purchase history aggregated into a PostgreSQL array using array_agg with DISTINCT and ORDER BY.
- `adv_customers_never_used_coupon` — Customers who have never redeemed a coupon, identified using the NOT EXISTS anti-join pattern against fct_coupon_redemptions. Includes a coupon opportunity segment for targeted marketing.
- `adv_dynamic_pricing_recommendation` — Business rule engine with 10+ pricing rules implemented as layered CASE expressions. Evaluates margin tier and sales velocity to recommend pricing actions such as discounts, increases, or discontinuation.
- …and 984 more — by domain: core (984), marketing (85), finance (85), product (85), supply_chain (85), hr_ops (80), cross_domain (44) (use `kg_search`)

**Metrics (19):**
- `average_order_value` (derived) — Average Order Value
- `count_lifetime_orders` (simple) — Count Lifetime Orders
- `cumulative_revenue` (cumulative) — Cumulative Revenue (All Time)
- `drink_orders` (simple) — Drink Orders
- `drink_revenue` (simple) — Drink Revenue
- `drink_revenue_pct` (ratio) — Drink Revenue %
- `food_orders` (simple) — Food Orders
- `food_revenue` (simple) — Food Revenue
- `food_revenue_pct` (ratio) — Food Revenue %
- `large_orders` (simple) — Large Orders
- `lifetime_spend_pretax` (simple) — LTV Pre-tax
- `median_revenue` (simple) — Median Revenue
- `new_customer_orders` (simple) — New Customers
- `order_cost` (simple) — Order Cost
- `order_gross_profit` (derived) — Order Gross Profit
- `order_total` (simple) — Order Total
- `orders` (simple) — Orders
- `revenue` (simple) — Revenue
- `revenue_growth_mom` (derived) — Revenue Growth % M/M

**Common dimensions:** customer_name, customer_order_number, customer_type, first_ordered_at, is_drink_item, is_drink_order, is_food_item, is_food_order, is_perishable_supply, last_ordered_at, location_name, opened_date, +10 more

**Exposures (22):**
- `crm_sync` (application) ← Marketing Ops
- `inventory_reorder_system` (application) ← Supply Chain Team
- `marketing_analytics` (dashboard) ← Marketing Team
- `ml_churn_prediction` (ml) ← Data Science Team
- `report_index` (dashboard) ← Data Platform
- `report_metrics_count_lifetime_orders` (dashboard) ← Data Platform
- `report_metrics_drink_orders` (dashboard) ← Data Platform
- `report_metrics_drink_revenue` (dashboard) ← Data Platform
- `report_metrics_drink_revenue_pct` (dashboard) ← Data Platform
- `report_metrics_food_orders` (dashboard) ← Data Platform
- `report_metrics_food_revenue` (dashboard) ← Data Platform
- `report_metrics_food_revenue_pct` (dashboard) ← Data Platform
- …and 10 more (use `kg_search`)

**Decisions (2):**
- `ADR-0002` — ADR-0002 — Snowflake's semantics are the ones we pin, on every adapter
- `ADR-0003` — ADR-0003 — What the base/current diff found

**Known gaps:**
- 57 raw table(s) reach no metric: `raw_accounts_receivable`, `raw_budgets`, `raw_campaign_spend`, `raw_campaigns`, `raw_coupon_redemptions`, `raw_coupons`, `raw_customers`, `raw_delivery_shipments`, `raw_departments`, `raw_email_events`, +47 more

_Query the graph before reading files: `kg_search`, `kg_neighbors`, `kg_path`._
