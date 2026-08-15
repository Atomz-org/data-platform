with

o as (
    select * from {{ ref('orders') }}
),

customer_first_order as (

    select
        customer_id,
        {{ dbt.date_trunc('month', 'first_ordered_at') }} as cohort_month
    from {{ ref('customers') }}
    where first_ordered_at is not null

),

order_months as (

    select
        o.customer_id,
        {{ dbt.date_trunc('month', 'o.ordered_at') }} as order_month,
        count(distinct o.order_id) as monthly_orders,
        sum(o.order_total) as monthly_revenue
    from o
    group by 1, 2

),

cohort_activity as (

    select
        cf.customer_id,
        cf.cohort_month,
        om.order_month,
        {{ dbt.datediff('cf.cohort_month', 'om.order_month', 'month') }} as months_since_first_order,
        om.monthly_orders,
        om.monthly_revenue

    from customer_first_order as cf
    inner join order_months as om
        on cf.customer_id = om.customer_id

)

select * from cohort_activity
