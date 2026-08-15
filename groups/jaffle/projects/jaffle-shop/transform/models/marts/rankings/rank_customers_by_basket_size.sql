with

customer_basket as (
    select customer_id, customer_name, avg_order_value, total_orders
    from {{ ref('dim_customer_360') }}
),

ranked as (
    select
        customer_id,
        customer_name,
        avg_order_value,
        total_orders,
        rank() over (order by avg_order_value desc) as basket_rank,
        ntile(10) over (order by avg_order_value desc) as basket_decile
    from customer_basket
    where avg_order_value > 0
)

select * from ranked
