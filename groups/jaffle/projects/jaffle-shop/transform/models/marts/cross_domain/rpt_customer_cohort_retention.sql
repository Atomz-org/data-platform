with customer_first_order as (
    select
        customer_id,
        {{ dbt.date_trunc("month", "min(ordered_at)") }} as cohort_month
    from {{ ref('orders') }}
    group by customer_id
),

customer_activity as (
    select
        o.customer_id,
        {{ dbt.date_trunc("month", "o.ordered_at") }} as activity_month
    from {{ ref('orders') }} as o
    group by o.customer_id, {{ dbt.date_trunc("month", "o.ordered_at") }}
),

cohort_activity as (
    select
        cfo.cohort_month,
        ca.activity_month,
        {{ dbt.datediff("cfo.cohort_month", "ca.activity_month", "month") }} as months_since_first_order,
        count(distinct ca.customer_id) as active_customers
    from customer_first_order as cfo
    inner join customer_activity as ca
        on cfo.customer_id = ca.customer_id
    group by cfo.cohort_month, ca.activity_month
),

cohort_sizes as (
    select
        cohort_month,
        count(distinct customer_id) as cohort_size
    from customer_first_order
    group by cohort_month
)

select
    ca.cohort_month,
    cs.cohort_size,
    ca.months_since_first_order,
    ca.active_customers,
    round(
        (cast(ca.active_customers as {{ dbt.type_float() }})
        / nullif(cs.cohort_size, 0) * 100), 2
    ) as retention_rate_pct,
    cs.cohort_size - ca.active_customers as churned_customers,
    round(
        (cast(cs.cohort_size - ca.active_customers as {{ dbt.type_float() }})
        / nullif(cs.cohort_size, 0) * 100), 2
    ) as churn_rate_pct
from cohort_activity as ca
inner join cohort_sizes as cs
    on ca.cohort_month = cs.cohort_month
order by ca.cohort_month, ca.months_since_first_order
