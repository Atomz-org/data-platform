with

cohort_activity as (

    select * from {{ ref('coh_customer_monthly_cohort') }}

),

revenue_by_period as (

    select
        cohort_month,
        months_since_first_order,
        sum(monthly_revenue) as period_revenue,
        count(distinct customer_id) as active_customers,
        case
            when count(distinct customer_id) > 0
            then sum(monthly_revenue) / count(distinct customer_id)
            else 0
        end as revenue_per_active_customer
    from cohort_activity
    group by 1, 2

),

with_cumulative as (

    select
        cohort_month,
        months_since_first_order,
        period_revenue,
        active_customers,
        revenue_per_active_customer,
        sum(period_revenue) over (
            partition by cohort_month
            order by months_since_first_order
            rows between unbounded preceding and current row
        ) as cumulative_revenue
    from revenue_by_period

)

select * from with_cumulative
