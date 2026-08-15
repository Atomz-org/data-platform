with

monthly_product as (
    select month_start, product_id, monthly_revenue, monthly_units
    from {{ ref('met_monthly_product_sales') }}
),

ranked as (
    select
        month_start,
        product_id,
        monthly_revenue,
        monthly_units,
        rank() over (partition by month_start order by monthly_revenue desc) as revenue_rank,
        round(monthly_revenue * 100.0 / nullif(sum(monthly_revenue) over (partition by month_start), 0), 2) as revenue_share_pct,
        ntile(5) over (partition by month_start order by monthly_revenue desc) as revenue_quintile
    from monthly_product
)

select * from ranked
