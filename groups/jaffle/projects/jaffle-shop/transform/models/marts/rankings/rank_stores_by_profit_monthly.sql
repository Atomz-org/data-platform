with

store_profit as (
    select
        month_start,
        location_id,
        monthly_revenue,
        monthly_revenue * 0.65 as estimated_profit
    from {{ ref('met_monthly_revenue_by_store') }}
),

ranked as (
    select
        month_start,
        location_id,
        monthly_revenue,
        estimated_profit,
        rank() over (partition by month_start order by estimated_profit desc) as profit_rank,
        round(estimated_profit * 100.0 / nullif(sum(estimated_profit) over (partition by month_start), 0), 2) as profit_share_pct,
        ntile(4) over (partition by month_start order by estimated_profit desc) as profit_quartile
    from store_profit
)

select * from ranked
