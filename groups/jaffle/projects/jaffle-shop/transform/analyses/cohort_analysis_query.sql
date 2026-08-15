-- Analysis: Ad-hoc cohort analysis
-- Groups customers by first-order month and tracks subsequent monthly activity

with customer_orders as (
    select
        c.customer_id,
        {{ sf_date_trunc('month', "c.first_ordered_at") }} as cohort_month,
        {{ sf_date_trunc('month', "o.ordered_at") }} as order_month
    from {{ ref('customers') }} c
    inner join {{ ref('orders') }} o on c.customer_id = o.customer_id
),

cohort_sizes as (
    select
        cohort_month,
        count(distinct customer_id) as cohort_size
    from customer_orders
    group by 1
),

cohort_activity as (
    select
        co.cohort_month,
        co.order_month,
        {{ sf_datediff('month', "co.cohort_month", "co.order_month") }} as months_since_first,
        count(distinct co.customer_id) as active_customers
    from customer_orders co
    group by 1, 2, 3
)

select
    ca.cohort_month,
    cs.cohort_size,
    ca.months_since_first,
    ca.active_customers,
    round(100.0 * ca.active_customers / cs.cohort_size, 1) as retention_pct
from cohort_activity ca
inner join cohort_sizes cs on ca.cohort_month = cs.cohort_month
where ca.months_since_first >= 0
order by ca.cohort_month, ca.months_since_first
