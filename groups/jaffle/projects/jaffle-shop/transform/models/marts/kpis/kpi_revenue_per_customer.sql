with monthly_rev as (
    select month_start, sum(monthly_revenue) as monthly_revenue
    from {{ ref('met_monthly_revenue_by_store') }}
    group by 1
),
monthly_cust as (
    select month_start, tracked_active_customers
    from {{ ref('met_monthly_customer_metrics') }}
),
final as (
    select
        r.month_start as month_start,
        r.monthly_revenue,
        c.tracked_active_customers,
        round(r.monthly_revenue * 1.0 / nullif(c.tracked_active_customers, 0), 2) as revenue_per_customer
    from monthly_rev as r
    inner join monthly_cust as c on r.month_start = c.month_start
)
select * from final
