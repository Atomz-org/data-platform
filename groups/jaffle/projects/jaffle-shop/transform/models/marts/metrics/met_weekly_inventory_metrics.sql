with

daily as (

    select * from {{ ref('met_daily_inventory_metrics') }}

),

weekly_agg as (

    select
        {{ dbt.date_trunc('week', 'movement_date') }} as week_start,
        location_id,
        location_name,
        sum(total_movements) as weekly_movements,
        sum(inbound_quantity) as weekly_inbound,
        sum(outbound_quantity) as weekly_outbound,
        avg(distinct_products_moved) as avg_daily_products_moved,
        max(products_in_stock) as products_in_stock,
        max(total_units_on_hand) as total_units_on_hand

    from daily
    group by 1, 2, 3

)

select * from weekly_agg
