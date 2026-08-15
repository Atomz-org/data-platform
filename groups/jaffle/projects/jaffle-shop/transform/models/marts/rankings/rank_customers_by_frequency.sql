with

customer_freq as (
    select customer_id, customer_name, total_orders, lifetime_spend
    from {{ ref('dim_customer_360') }}
),

ranked as (
    select
        customer_id,
        customer_name,
        total_orders,
        lifetime_spend,
        rank() over (order by total_orders desc) as frequency_rank,
        ntile(10) over (order by total_orders desc) as frequency_decile
    from customer_freq
    where total_orders > 0
)

select * from ranked
