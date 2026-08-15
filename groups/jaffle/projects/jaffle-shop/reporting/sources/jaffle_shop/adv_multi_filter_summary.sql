-- source extract for adv_multi_filter_summary (PII columns excluded by the MDL projection)
select location_id, weekend_orders, weekday_orders, weekend_revenue, weekday_revenue, q1_revenue, q2_revenue, q3_revenue, q4_revenue, high_value_customers, mid_value_customers, low_value_customers, weekend_combo_repeat_orders, first_time_food_revenue, avg_items_repeat_drink_only
from main_marts.adv_multi_filter_summary
