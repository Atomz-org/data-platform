-- source extract for rpt_product_lifecycle_stage (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, sale_month, monthly_units_sold, monthly_revenue, month_number, total_months, rolling_3m_avg_units, peak_monthly_units, prev_month_units, prev_2_month_units, latest_mom_change_pct, pct_of_peak, lifecycle_stage
from main_marts.rpt_product_lifecycle_stage
