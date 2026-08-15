-- source extract for ml_feature_demand_forecast (PII columns excluded by the MDL projection)
select product_id, store_id, week_start, weekly_units, trailing_4w_avg_units, trailing_8w_avg_units, seasonality_index, month_of_year, weekly_orders, same_week_prior_year_units, prior_week_units
from main_marts.ml_feature_demand_forecast
