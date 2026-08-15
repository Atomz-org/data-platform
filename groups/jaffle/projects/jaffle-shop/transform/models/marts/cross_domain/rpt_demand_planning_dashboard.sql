with supply_data as (
    select
        product_id,
        total_stock_on_hand,
        stocked_locations,
        total_stock_value,
        weekly_demand_forecast,
        safety_stock_demand,
        supply_demand_gap,
        weeks_of_supply,
        stock_status
    from {{ ref('int_supply_capacity') }}
),

product_info as (
    select
        product_id,
        product_name
    from {{ ref('products') }}
),

demand_trend as (
    select
        product_id,
        actual_quantity,
        forecasted_quantity,
        forecast_error_pct,
        quantity_volatility,
        recency_rank
    from {{ ref('int_demand_forecast_weekly') }}
    where recency_rank <= 4
),

demand_trend_summary as (
    select
        product_id,
        avg(actual_quantity) as avg_recent_demand,
        avg(forecast_error_pct) as avg_forecast_error,
        max(quantity_volatility) as max_volatility,
        max(case when recency_rank = 1 then actual_quantity end) as latest_week_demand,
        max(case when recency_rank = 4 then actual_quantity end) as four_weeks_ago_demand
    from demand_trend
    group by product_id
)

select
    sd.product_id,
    pi.product_name,
    sd.total_stock_on_hand,
    sd.stocked_locations,
    sd.total_stock_value,
    sd.weekly_demand_forecast,
    sd.safety_stock_demand,
    sd.supply_demand_gap,
    sd.weeks_of_supply,
    sd.stock_status,
    dts.avg_recent_demand,
    dts.avg_forecast_error,
    dts.max_volatility,
    case
        when dts.four_weeks_ago_demand > 0
            then round(
                (dts.latest_week_demand - dts.four_weeks_ago_demand)
                / dts.four_weeks_ago_demand * 100, 2
            )
        else 0
    end as demand_trend_pct,
    case
        when sd.stock_status = 'out_of_stock' then 1
        when sd.stock_status = 'critical_low' then 2
        when sd.stock_status = 'low' then 3
        when sd.stock_status = 'overstock' then 4
        else 5
    end as action_priority,
    case
        when sd.stock_status in ('out_of_stock', 'critical_low') then 'urgent_reorder'
        when sd.stock_status = 'low' then 'reorder_soon'
        when sd.stock_status = 'overstock' then 'reduce_orders'
        else 'no_action'
    end as recommended_action
from supply_data as sd
left join product_info as pi
    on sd.product_id = pi.product_id
left join demand_trend_summary as dts
    on sd.product_id = dts.product_id
