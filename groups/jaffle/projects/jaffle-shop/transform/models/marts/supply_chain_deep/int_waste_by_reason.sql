with

waste_logs as (

    select * from {{ ref('stg_waste_logs') }}

),

final as (

    select
        waste_reason,
        location_id,
        {{ dbt.date_trunc('month', 'wasted_at') }} as waste_month,
        count(waste_log_id) as waste_event_count,
        sum(quantity_wasted) as total_quantity_wasted,
        sum(cost_of_waste) as total_waste_cost,
        avg(cost_of_waste) as avg_waste_cost_per_event,
        count(distinct product_id) as distinct_products_wasted
    from waste_logs
    group by 1, 2, 3

)

select * from final
