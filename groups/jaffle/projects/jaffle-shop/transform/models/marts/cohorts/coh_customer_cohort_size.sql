with

o as (
    select * from {{ ref('stg_orders') }}
),

c as (
    select * from {{ ref('stg_customers') }}
),

customer_first_order as (

    select
        o.customer_id,
        {{ dbt.date_trunc('month', 'min(o.ordered_at)') }} as cohort_month
    from o
    inner join c
        on o.customer_id = c.customer_id
    group by 1

),

cohort_sizes as (

    select
        cohort_month,
        count(distinct customer_id) as new_customers,
        row_number() over (order by cohort_month) as cohort_number
    from customer_first_order
    group by 1

),

with_cumulative as (

    select
        cohort_month,
        cohort_number,
        new_customers,
        sum(new_customers) over (
            order by cohort_month
            rows between unbounded preceding and current row
        ) as cumulative_customers
    from cohort_sizes

)

select * from with_cumulative
