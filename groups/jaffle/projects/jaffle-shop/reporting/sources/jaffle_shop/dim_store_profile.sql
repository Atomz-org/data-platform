-- source extract for dim_store_profile (PII columns excluded by the MDL projection)
select location_id, store_id, store_name, total_revenue, total_expenses, total_labor_cost, total_net_income, avg_operating_margin_pct, months_of_data, avg_labor_cost_pct, distinct_products_stocked, total_inventory_value, estimated_monthly_holding_cost, total_marketing_spend, avg_monthly_marketing_spend, avg_staffing_ratio, avg_employee_count
from main_marts.dim_store_profile
