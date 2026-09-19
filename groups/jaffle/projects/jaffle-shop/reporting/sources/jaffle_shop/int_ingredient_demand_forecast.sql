-- source extract for int_ingredient_demand_forecast (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    supply_id,
    supply_name,
    demand_week,
    units_ordered,
    forecast_units_4wk_avg,
    forecast_cost_4wk_avg
from main_marts.int_ingredient_demand_forecast
