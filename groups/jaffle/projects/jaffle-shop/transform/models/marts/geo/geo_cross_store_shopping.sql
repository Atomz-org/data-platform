with

orders as (

    select * from {{ ref('stg_orders') }}

),

customer_stores as (

    select
        customer_id,
        count(distinct location_id) as distinct_stores,
        count(*) as total_orders,
        min(ordered_at) as first_order_at,
        max(ordered_at) as last_order_at

    from orders
    where customer_id is not null
    group by customer_id

),

multi_store as (

    select * from customer_stores where distinct_stores > 1

)

select
    customer_id,
    distinct_stores,
    total_orders,
    first_order_at,
    last_order_at,
    round(total_orders * 1.0 / distinct_stores, 2) as avg_orders_per_store,
    case
        when distinct_stores >= 4 then 'highly_mobile'
        when distinct_stores >= 2 then 'multi_store'
        else 'single_store'
    end as shopping_pattern

from customer_stores
