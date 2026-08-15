with

o as (
    select * from {{ ref('stg_orders') }}
),

monthly_store_customers as (
    select
        {{ sf_date_trunc('month', "o.ordered_at") }} as order_month,
        o.location_id,
        count(distinct o.customer_id) as customer_count
    from o
    group by 1, 2
),

ranked as (
    select
        order_month,
        location_id,
        customer_count,
        rank() over (partition by order_month order by customer_count desc) as customer_rank,
        ntile(4) over (partition by order_month order by customer_count desc) as customer_quartile
    from monthly_store_customers
)

select * from ranked
