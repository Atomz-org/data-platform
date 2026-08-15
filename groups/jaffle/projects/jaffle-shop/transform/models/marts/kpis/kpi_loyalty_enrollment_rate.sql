with monthly_enrollments as (
    select
        {{ sf_date_trunc('month', "enrolled_at") }} as enrollment_month,
        count(*) as new_enrollments
    from {{ ref('dim_loyalty_members') }}
    group by 1
),
monthly_customers as (
    select month_start, tracked_active_customers
    from {{ ref('met_monthly_customer_metrics') }}
),
final as (
    select
        e.enrollment_month,
        e.new_enrollments,
        c.tracked_active_customers,
        round(e.new_enrollments * 100.0 / nullif(c.tracked_active_customers, 0), 2) as enrollment_rate_pct
    from monthly_enrollments as e
    inner join monthly_customers as c on e.enrollment_month = c.month_start
)
select * from final
