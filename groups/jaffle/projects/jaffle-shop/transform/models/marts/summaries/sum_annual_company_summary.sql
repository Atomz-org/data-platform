with monthly as (
    select month_start, sum(monthly_revenue) as monthly_revenue, sum(monthly_orders) as total_orders
    from {{ ref('met_monthly_revenue_by_store') }}
    group by 1
),
final as (
    select
        {{ sf_date_trunc('year', "month_start") }} as fiscal_year,
        sum(monthly_revenue) as annual_revenue,
        sum(total_orders) as annual_orders,
        round(sum(monthly_revenue) * 1.0 / nullif(sum(total_orders), 0), 2) as annual_aov,
        round(avg(monthly_revenue), 2) as avg_monthly_revenue,
        min(monthly_revenue) as min_monthly_revenue,
        max(monthly_revenue) as max_monthly_revenue
    from monthly
    group by 1
)
select * from final
