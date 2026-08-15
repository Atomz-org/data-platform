with

customer_ltv as (
    select
        customer_id,
        customer_name,
        lifetime_spend,
        total_orders,
        avg_order_value
    from {{ ref('dim_customer_360') }}
),

ranked as (
    select
        customer_id,
        customer_name,
        lifetime_spend,
        total_orders,
        avg_order_value,
        rank() over (order by lifetime_spend desc) as ltv_rank,
        ntile(10) over (order by lifetime_spend desc) as ltv_decile,
        round(lifetime_spend * 100.0 / nullif(sum(lifetime_spend) over (), 0), 4) as revenue_share_pct,
        sum(lifetime_spend) over (order by lifetime_spend desc) as cumulative_revenue
    from customer_ltv
    where lifetime_spend > 0
)

select * from ranked
