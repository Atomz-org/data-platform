-- source extract for int_demand_forecast_weekly (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    sale_week,
    forecasted_quantity,
    forecast_error_pct
from main_marts.int_demand_forecast_weekly
