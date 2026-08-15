-- source extract for rpt_store_opening_playbook (PII columns excluded by the MDL projection)
select store_id, avg_monthly_revenue_first_6m, store_name, months_of_data, total_revenue, avg_operating_margin_pct, total_revenue_first_6m, total_orders_first_6m, first_6m_pct_of_total_revenue
from main_marts.rpt_store_opening_playbook
