-- source extract for fin_store_roi (PII columns excluded by the MDL projection)
select location_id, store_name, report_month, monthly_revenue, net_profit, opened_date, months_open, cumulative_profit, cumulative_revenue, estimated_setup_cost, roi_pct
from main_marts.fin_store_roi
