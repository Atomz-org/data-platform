with 
o as (
    select * from {{ ref('stg_orders') }}
),

order_hours as (
    select
        o.order_id,
        o.location_id as store_id,
        o.ordered_at,
        cast({{ dbt.date_trunc("day", "o.ordered_at") }} as date) as order_date,
        extract(hour from o.ordered_at) as order_hour,
        o.order_total
    from o
),

hourly_agg as (
    select
        store_id,
        order_date,
        order_hour,
        count(distinct order_id) as orders_in_hour,
        sum(order_total) as revenue_in_hour
    from order_hours
    group by store_id, order_date, order_hour
),

store_hour_avg as (
    select
        store_id,
        order_hour,
        round(avg(cast(orders_in_hour as {{ dbt.type_float() }})), 2) as avg_orders_per_hour,
        round(avg(cast(revenue_in_hour as {{ dbt.type_float() }})), 2) as avg_revenue_per_hour,
        count(distinct order_date) as days_with_data,
        max(orders_in_hour) as peak_orders_in_hour,
        sum(orders_in_hour) as total_orders_in_hour
    from hourly_agg
    group by store_id, order_hour
)

select
    store_id,
    order_hour,
    avg_orders_per_hour,
    avg_revenue_per_hour,
    days_with_data,
    peak_orders_in_hour,
    total_orders_in_hour,
    sum(total_orders_in_hour) over (partition by store_id) as store_total_orders,
    round(
        cast(total_orders_in_hour as {{ dbt.type_float() }})
        / nullif(sum(total_orders_in_hour) over (partition by store_id), 0) * 100, 2
    ) as hour_share_of_total_pct
from store_hour_avg
