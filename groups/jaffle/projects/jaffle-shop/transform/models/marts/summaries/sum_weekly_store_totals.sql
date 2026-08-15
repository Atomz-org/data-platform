with

r as (
    select * from {{ ref('int_revenue_by_store_daily') }}
),

weekly_agg as (
    select
        {{ dbt.date_trunc('week', 'r.revenue_date') }} as week_start,
        r.location_id,
        sum(r.total_revenue) as weekly_revenue,
        sum(r.invoice_count) as weekly_orders,
        round(sum(r.total_revenue) * 1.0 / nullif(sum(r.invoice_count), 0), 2) as avg_order_value,
        0 as labor_cost
    from r
    group by 1, 2
),

final as (
    select
        week_start,
        location_id,
        weekly_revenue,
        weekly_orders,
        avg_order_value,
        labor_cost,
        lag(weekly_revenue) over (partition by location_id order by week_start) as prior_week_revenue
    from weekly_agg
)

select * from final
