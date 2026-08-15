with

customer_recency as (
    select customer_id, customer_name, days_since_last_order, total_orders
    from {{ ref('dim_customer_360') }}
),

ranked as (
    select
        customer_id,
        customer_name,
        days_since_last_order,
        total_orders,
        rank() over (order by days_since_last_order asc) as recency_rank,
        ntile(10) over (order by days_since_last_order asc) as recency_decile,
        case
            when days_since_last_order <= 7 then 'this_week'
            when days_since_last_order <= 30 then 'this_month'
            when days_since_last_order <= 90 then 'this_quarter'
            else 'dormant'
        end as recency_band
    from customer_recency
    where days_since_last_order is not null
)

select * from ranked
