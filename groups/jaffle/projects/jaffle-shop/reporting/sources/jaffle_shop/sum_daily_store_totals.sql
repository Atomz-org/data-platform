-- source extract for sum_daily_store_totals (PII columns excluded by the MDL projection)
select waste_date, location_id, total_revenue, invoice_count, avg_order_value, labor_cost, waste_cost, net_contribution
from main_marts.sum_daily_store_totals
