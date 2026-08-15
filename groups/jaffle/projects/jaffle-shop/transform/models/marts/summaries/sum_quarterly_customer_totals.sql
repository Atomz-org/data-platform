with monthly as (
    select
        month_start,
        tracked_active_customers,
        new_customers
    from {{ ref('met_monthly_customer_metrics') }}
),
final as (
    select
        {{ sf_date_trunc('quarter', "month_start") }} as metric_quarter,
        sum(tracked_active_customers) as total_customer_months,
        sum(new_customers) as total_new_customers,
        round(avg(tracked_active_customers), 0) as avg_monthly_customers
    from monthly
    group by 1
)
select * from final
