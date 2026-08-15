-- source extract for cmp_weekday_vs_weekend (PII columns excluded by the MDL projection)
select location_id, weekday_avg_revenue_per_day, weekend_avg_revenue_per_day, weekend_revenue_lift_pct, weekend_ticket_lift_pct, weekday_orders, weekday_avg_orders_per_day, weekday_avg_ticket, weekday_unique_customers, weekend_orders, weekend_avg_orders_per_day, weekend_avg_ticket, weekend_unique_customers
from main_marts.cmp_weekday_vs_weekend
