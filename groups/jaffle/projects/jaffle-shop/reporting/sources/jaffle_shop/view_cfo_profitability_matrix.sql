-- source extract for view_cfo_profitability_matrix (PII columns excluded by the MDL projection)
select location_id, avg_monthly_revenue, avg_net_margin_pct, avg_net_profit_margin_pct, six_month_revenue, six_month_net_profit, margin_rank, revenue_rank, margin_category
from main_marts.view_cfo_profitability_matrix
