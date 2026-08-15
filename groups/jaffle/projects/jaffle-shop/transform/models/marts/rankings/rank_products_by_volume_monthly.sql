with

monthly_product as (
    select month_start, product_id, monthly_units, monthly_revenue
    from {{ ref('met_monthly_product_sales') }}
),

ranked as (
    select
        month_start,
        product_id,
        monthly_units,
        monthly_revenue,
        rank() over (partition by month_start order by monthly_units desc) as volume_rank,
        round(monthly_units * 100.0 / nullif(sum(monthly_units) over (partition by month_start), 0), 2) as volume_share_pct,
        ntile(5) over (partition by month_start order by monthly_units desc) as volume_quintile
    from monthly_product
)

select * from ranked
