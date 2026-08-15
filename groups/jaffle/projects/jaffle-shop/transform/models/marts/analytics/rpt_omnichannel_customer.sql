with

orders as (

    select * from {{ ref('stg_orders') }}

),

customer_stores as (

    select
        customer_id,
        count(distinct location_id) as stores_visited,
        count(distinct order_id) as total_orders,
        sum(order_total) as total_spend,
        min(ordered_at) as first_order_date,
        max(ordered_at) as last_order_date
    from orders
    group by 1

),

final as (

    select
        customer_id,
        stores_visited,
        total_orders,
        total_spend,
        first_order_date,
        last_order_date,
        case
            when stores_visited = 1 then 'single_store'
            when stores_visited = 2 then 'dual_store'
            else 'multi_store'
        end as store_engagement_tier,
        case
            when total_orders > 0
                then round(cast(total_spend / total_orders as {{ dbt.type_float() }}), 2)
            else 0
        end as avg_order_value,
        round(cast(total_orders * 1.0 / stores_visited as {{ dbt.type_float() }}), 2) as orders_per_store
    from customer_stores

)

select * from final
