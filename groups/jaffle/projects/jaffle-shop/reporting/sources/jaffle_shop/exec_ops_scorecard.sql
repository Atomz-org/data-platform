-- source extract for exec_ops_scorecard (PII columns excluded by the MDL projection)
select reporting_month, ops_health_score, avg_orders_per_labor_hour, waste_to_revenue_pct, avg_employee_performance_score, labor_cost_pct, total_labor_cost, inventory_movements, avg_products_in_stock, total_inbound, total_outbound, waste_cost, waste_events, top_performers, needs_support_count, total_scored_employees
from main_marts.exec_ops_scorecard
