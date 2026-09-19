-- source extract for ml_feature_demand_forecast (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    store_id,
    week_start,
    weekly_units,
    trailing_4w_avg_units,
    trailing_8w_avg_units,
    seasonality_index
from main_marts.ml_feature_demand_forecast
