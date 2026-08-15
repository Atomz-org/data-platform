-- source extract for view_coo_ops_dashboard (PII columns excluded by the MDL projection)
select reporting_month, avg_order_throughput, labor_utilization_pct, waste_rate_pct, overall_ops_score, ops_rating
from main_marts.view_coo_ops_dashboard
