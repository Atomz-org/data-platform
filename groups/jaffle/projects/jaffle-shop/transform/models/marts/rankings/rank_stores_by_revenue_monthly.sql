with

monthly_store as (
    select month_start, location_id, monthly_revenue, monthly_orders
    from {{ ref('met_monthly_revenue_by_store') }}
),

ranked as (
    select
        month_start,
        location_id,
        monthly_revenue,
        monthly_orders,
        rank() over (partition by month_start order by monthly_revenue desc) as revenue_rank,
        dense_rank() over (partition by month_start order by monthly_revenue desc) as revenue_dense_rank,
        round((monthly_revenue * 100.0 / nullif(sum(monthly_revenue) over (partition by month_start), 0)), 2) as revenue_share_pct,
        ntile(4) over (partition by month_start order by monthly_revenue desc) as revenue_quartile
    from monthly_store
)

select * from ranked
