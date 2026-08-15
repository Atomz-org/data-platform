-- source extract for sc_economic_order_quantity (PII columns excluded by the MDL projection)
select ingredient_id, ingredient_name, avg_daily_usage, annual_demand, avg_unit_cost, ordering_cost_per_order, annual_holding_cost_per_unit, economic_order_quantity, orders_per_year
from main_marts.sc_economic_order_quantity
