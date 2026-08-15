with

orders as (

    select * from {{ ref('stg_orders') }}

),

customers as (

    select * from {{ ref('stg_customers') }}

),

monthly_customer_revenue as (

    select
        o.customer_id,
        c.customer_name,
        {{ dbt.date_trunc('month', 'o.ordered_at') }} as revenue_month,
        count(distinct o.order_id) as order_count,
        sum(o.order_total) as total_revenue,
        avg(o.order_total) as avg_order_value
    from orders as o
    left join customers as c
        on o.customer_id = c.customer_id
    group by 1, 2, 3

)

select * from monthly_customer_revenue
