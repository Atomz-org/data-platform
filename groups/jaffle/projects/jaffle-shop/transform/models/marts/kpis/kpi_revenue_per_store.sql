with monthly as (
    select month_start, location_id, monthly_revenue
    from {{ ref('met_monthly_revenue_by_store') }}
),
final as (
    select
        month_start,
        count(distinct location_id) as store_count,
        sum(monthly_revenue) as monthly_revenue,
        round(sum(monthly_revenue) * 1.0 / nullif(count(distinct location_id), 0), 2) as revenue_per_store,
        lag(round((sum(monthly_revenue) * 1.0 / nullif(count(distinct location_id), 0)), 2)) over (order by month_start) as prior_month_rps
    from monthly
    group by 1
)
select * from final
