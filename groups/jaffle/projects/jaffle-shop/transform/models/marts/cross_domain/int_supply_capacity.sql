with latest_forecast as (
    select
        product_id,
        forecasted_quantity as weekly_demand_forecast,
        quantity_volatility,
        forecasted_quantity + 2 * coalesce(quantity_volatility, 0) as safety_stock_demand
    from {{ ref('int_demand_forecast_weekly') }}
    where recency_rank = 1
),

current_stock as (
    select
        product_id,
        location_id,
        current_quantity
    from {{ ref('int_inventory_current_level') }}
),

stock_by_product as (
    select
        product_id,
        sum(current_quantity) as total_stock_on_hand,
        count(distinct location_id) as stocked_locations,
        0 as total_stock_value
    from current_stock
    group by product_id
)

select
    coalesce(cast(lf.product_id as {{ dbt.type_string() }}), cast(sp.product_id as {{ dbt.type_string() }})) as product_id,
    coalesce(sp.total_stock_on_hand, 0) as total_stock_on_hand,
    sp.stocked_locations,
    coalesce(sp.total_stock_value, 0) as total_stock_value,
    coalesce(lf.weekly_demand_forecast, 0) as weekly_demand_forecast,
    coalesce(lf.safety_stock_demand, 0) as safety_stock_demand,
    coalesce(sp.total_stock_on_hand, 0) - coalesce(lf.weekly_demand_forecast, 0) as supply_demand_gap,
    case
        when coalesce(lf.weekly_demand_forecast, 0) > 0
            then round(
                (cast(coalesce(sp.total_stock_on_hand, 0) as {{ dbt.type_float() }})
                / lf.weekly_demand_forecast), 2
            )
        else null
    end as weeks_of_supply,
    case
        when coalesce(sp.total_stock_on_hand, 0) <= 0 then 'out_of_stock'
        when coalesce(sp.total_stock_on_hand, 0) < coalesce(lf.safety_stock_demand, 0) then 'critical_low'
        when coalesce(sp.total_stock_on_hand, 0) < coalesce(lf.weekly_demand_forecast, 0) * 2 then 'low'
        when coalesce(sp.total_stock_on_hand, 0) > coalesce(lf.weekly_demand_forecast, 0) * 8 then 'overstock'
        else 'adequate'
    end as stock_status
from latest_forecast as lf
full outer join stock_by_product as sp
    on cast(lf.product_id as {{ dbt.type_string() }}) = cast(sp.product_id as {{ dbt.type_string() }})
