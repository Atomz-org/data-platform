-- source extract for adv_conditional_aggregates (PII columns excluded by the MDL projection)
select location_id, total_orders, unique_customers, total_revenue, food_orders, drink_orders, combo_orders, other_orders, first_order_revenue, repeat_order_revenue, repeat_customer_aov, new_customer_aov, large_orders, large_order_avg, avg_items_food_orders, avg_items_drink_orders
from main_marts.adv_conditional_aggregates
