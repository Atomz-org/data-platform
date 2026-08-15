with customer_ltv as (
    select * from {{ ref('int_customer_ltv') }}
),

buckets as (
    select
        ltv_tier,
        count(*) as customer_count,
        avg(lifetime_spend) as avg_lifetime_spend,
        min(lifetime_spend) as min_lifetime_spend,
        max(lifetime_spend) as max_lifetime_spend,
        avg(total_orders) as avg_orders
    from customer_ltv
    group by ltv_tier
)

select * from buckets
