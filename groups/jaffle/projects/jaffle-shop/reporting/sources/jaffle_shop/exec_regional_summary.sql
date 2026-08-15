-- source extract for exec_regional_summary (PII columns excluded by the MDL projection)
select location_id, store_name, pnl_total_revenue, net_profit_margin_pct, profile_total_revenue, avg_operating_margin_pct, avg_labor_cost_pct, avg_employee_count, total_net_profit, avg_net_margin_pct, pnl_avg_labor_ratio_pct, months_of_data
from main_marts.exec_regional_summary
