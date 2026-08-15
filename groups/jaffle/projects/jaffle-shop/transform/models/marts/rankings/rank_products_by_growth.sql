with

monthly_product as (
    select month_start, product_id, monthly_revenue
    from {{ ref('met_monthly_product_sales') }}
),

with_growth as (
    select
        month_start,
        product_id,
        monthly_revenue,
        lag(monthly_revenue) over (partition by product_id order by month_start) as prior_month_revenue,
        round(((monthly_revenue - lag(monthly_revenue) over (partition by product_id order by month_start))) * 100.0
            / nullif(lag(monthly_revenue) over (partition by product_id order by month_start), 0), 2) as growth_pct
    from monthly_product
),

ranked as (
    select
        month_start,
        product_id,
        monthly_revenue,
        growth_pct,
        rank() over (partition by month_start order by growth_pct desc) as growth_rank
    from with_growth
    where growth_pct is not null
)

select * from ranked
