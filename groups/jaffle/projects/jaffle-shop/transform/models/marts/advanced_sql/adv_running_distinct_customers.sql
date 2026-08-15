-- adv_running_distinct_customers.sql
-- Technique: Window Function Trick — Running count of distinct values
-- COUNT(DISTINCT ...) OVER() is not supported in SQL, so we use dense_rank()
-- to assign each customer their first-appearance date, then do a cumulative count
-- of those first appearances.

with orders as (

    select * from {{ ref('stg_orders') }}

),

-- Find each customer's first order date
customer_first_order as (

    select
        customer_id,
        min(ordered_at) as first_order_date
    from orders
    group by 1

),

-- Count new customers per day (those whose first order was on that day)
new_customers_per_day as (

    select
        first_order_date as date_day,
        count(customer_id) as new_customers_today
    from customer_first_order
    group by 1

),

-- Get daily order stats
daily_orders as (

    select
        ordered_at as date_day,
        count(order_id) as orders_today,
        sum(order_total) as revenue_today,
        count(distinct customer_id) as active_customers_today
    from orders
    group by 1

),

-- Combine and compute running distinct customer count
final as (

    select
        d.date_day,
        d.orders_today,
        d.revenue_today,
        d.active_customers_today,
        coalesce(nc.new_customers_today, 0) as new_customers_today,

        -- Cumulative sum of new customers = running count of distinct customers
        sum(coalesce(nc.new_customers_today, 0)) over (
            order by d.date_day
            rows between unbounded preceding and current row
        ) as cumulative_distinct_customers

    from daily_orders as d
    left join new_customers_per_day as nc
        on d.date_day = nc.date_day

)

select * from final
order by date_day
