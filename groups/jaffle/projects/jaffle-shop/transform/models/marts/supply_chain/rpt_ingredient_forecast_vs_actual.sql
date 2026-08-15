with

forecast as (

    select * from {{ ref('int_ingredient_demand_forecast') }}

),

depletion as (

    select * from {{ ref('int_stock_depletion_rate') }}

),

latest_forecast as (

    select
        product_id,
        supply_id,
        supply_name,
        demand_week,
        units_ordered as actual_units,
        forecast_units_4wk_avg as forecasted_units,
        total_ingredient_cost as actual_cost,
        forecast_cost_4wk_avg as forecasted_cost,
        case
            when forecast_units_4wk_avg > 0
                then (units_ordered - forecast_units_4wk_avg) * 1.0
                    / forecast_units_4wk_avg
            else null
        end as forecast_variance_pct,
        case
            when forecast_units_4wk_avg > 0
                then abs(units_ordered - forecast_units_4wk_avg) * 1.0
                    / forecast_units_4wk_avg
            else null
        end as forecast_error_pct

    from forecast

),

with_stock_context as (

    select
        latest_forecast.product_id,
        latest_forecast.supply_id,
        latest_forecast.supply_name,
        latest_forecast.demand_week,
        latest_forecast.actual_units,
        latest_forecast.forecasted_units,
        latest_forecast.actual_cost,
        latest_forecast.forecasted_cost,
        latest_forecast.forecast_variance_pct,
        latest_forecast.forecast_error_pct,
        depletion.current_quantity as current_stock,
        depletion.daily_depletion_rate,
        depletion.estimated_days_of_stock

    from latest_forecast

    left join depletion
        on latest_forecast.product_id = depletion.product_id

)

select * from with_stock_context
