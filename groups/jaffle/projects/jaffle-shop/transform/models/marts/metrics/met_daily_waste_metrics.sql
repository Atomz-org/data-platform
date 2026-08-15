with

waste as (

    select * from {{ ref('fct_waste_events') }}

),

daily_waste as (

    select
        {{ dbt.date_trunc('day', 'wasted_at') }} as waste_date,
        location_id,
        location_name,
        count(waste_log_id) as waste_events,
        sum(quantity_wasted) as total_quantity_wasted,
        sum(cost_of_waste) as total_waste_cost,
        count(distinct product_id) as distinct_products_wasted,
        count(distinct waste_reason) as distinct_waste_reasons

    from waste
    group by 1, 2, 3

)

select * from daily_waste
