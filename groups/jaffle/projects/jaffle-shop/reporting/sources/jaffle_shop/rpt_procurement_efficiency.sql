-- source extract for rpt_procurement_efficiency (PII columns excluded by the MDL projection)
select supplier_id, supplier_name, order_month, count_orders, avg_cycle_time_days, min_cycle_time_days, max_cycle_time_days, avg_expected_cycle_time_days, avg_cycle_time_variance_days, count_on_time_or_early, count_late, on_time_rate, cycle_time_efficiency_ratio
from main_marts.rpt_procurement_efficiency
