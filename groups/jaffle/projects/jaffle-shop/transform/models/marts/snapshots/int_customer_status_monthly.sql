with

orders as (

    select * from {{ ref('stg_orders') }}

),

-- Generate month boundaries from order data
months as (

    select distinct
        {{ dbt.date_trunc('month', 'ordered_at') }} as month_start

    from orders

),

-- All customers who have ever ordered
all_customers as (

    select distinct customer_id
    from orders

),

-- Cross join to evaluate every customer for every month
customer_months as (

    select
        m.month_start,
        c.customer_id

    from months as m
    cross join all_customers as c

),

-- Last order date as of each month end
customer_activity as (

    select
        month_start,
        cm.customer_id,
        max(o.ordered_at) as last_order_date,
        count(o.order_id) as lifetime_orders

    from customer_months as cm

    left join orders as o
        on cm.customer_id = o.customer_id
        and o.ordered_at <= month_start + interval '1 month' - interval '1 day'

    group by 1, 2
    having max(o.ordered_at) is not null

),

-- Classify status based on recency
classified as (

    select
        month_start,
        customer_id,
        last_order_date,
        lifetime_orders,
        {{ sf_datediff('day', "last_order_date", "(month_start + interval '1 month' - interval '1 day')") }} as days_since_last_order,
        case
            when {{ sf_datediff('day', "last_order_date", "(month_start + interval '1 month' - interval '1 day')") }} <= 90
                then 'active'
            when {{ sf_datediff('day', "last_order_date", "(month_start + interval '1 month' - interval '1 day')") }} <= 180
                then 'dormant'
            else 'churned'
        end as customer_status

    from customer_activity as cm

)

select * from classified
