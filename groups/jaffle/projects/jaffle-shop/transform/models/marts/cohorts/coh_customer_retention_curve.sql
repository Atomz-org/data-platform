with

cohort_activity as (

    select * from {{ ref('coh_customer_monthly_cohort') }}

),

cohort_sizes as (

    select
        cohort_month,
        count(distinct customer_id) as cohort_size
    from cohort_activity
    where months_since_first_order = 0
    group by 1

),

active_per_period as (

    select
        cohort_month,
        months_since_first_order,
        count(distinct customer_id) as active_customers
    from cohort_activity
    where months_since_first_order between 0 and 12
    group by 1, 2

),

retention_curve as (

    select
        a.cohort_month,
        a.months_since_first_order,
        cs.cohort_size,
        a.active_customers,
        round(
            (a.active_customers * 100.0 / nullif(cs.cohort_size, 0)), 2
        ) as retention_rate_pct
    from active_per_period as a
    inner join cohort_sizes as cs
        on a.cohort_month = cs.cohort_month

)

select * from retention_curve
