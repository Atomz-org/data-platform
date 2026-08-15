with

daily as (

    select * from {{ ref('met_daily_inventory_metrics') }}

),

monthly_agg as (

    select
        {{ dbt.date_trunc('month', 'movement_date') }} as month_start,
        location_id,
        location_name,
        sum(total_movements) as monthly_movements,
        sum(inbound_quantity) as monthly_inbound,
        sum(outbound_quantity) as monthly_outbound,
        avg(distinct_products_moved) as avg_daily_products_moved,
        max(products_in_stock) as products_in_stock,
        max(total_units_on_hand) as total_units_on_hand

    from daily
    group by 1, 2, 3

),

with_change as (

    select
        *,
        lag(monthly_movements) over (
            partition by location_id order by month_start
        ) as prev_month_movements,
        case
            when lag(monthly_movements) over (
                partition by location_id order by month_start
            ) > 0
            then (monthly_movements - lag(monthly_movements) over (
                partition by location_id order by month_start
            )) * 1.0 / lag(monthly_movements) over (
                partition by location_id order by month_start
            )
        end as mom_movement_change

    from monthly_agg

)

select * from with_change
