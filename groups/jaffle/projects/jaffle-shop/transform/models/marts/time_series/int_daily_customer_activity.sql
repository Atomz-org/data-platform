with

orders as (

    select * from {{ ref('stg_orders') }}

),

customers as (

    select * from {{ ref('customers') }}

),

-- Unique customers per day
daily_customers as (

    select
        o.ordered_at as activity_date,
        count(distinct o.customer_id) as unique_customers,
        count(o.order_id) as total_orders,
        sum(o.order_total) as total_revenue

    from orders as o
    group by 1

),

-- New customers per day (first order date)
new_customers_per_day as (

    select
        first_ordered_at as activity_date,
        count(customer_id) as new_customers

    from customers
    where first_ordered_at is not null
    group by 1

),

final as (

    select
        dc.activity_date,
        dc.unique_customers,
        dc.total_orders,
        dc.total_revenue,
        coalesce(nc.new_customers, 0) as new_customers,
        dc.unique_customers - coalesce(nc.new_customers, 0) as returning_customers

    from daily_customers as dc

    left join new_customers_per_day as nc
        on dc.activity_date = nc.activity_date

)

select * from final
