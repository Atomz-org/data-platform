with

orders as (

    select * from {{ ref('stg_orders') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

hourly_orders as (

    select
        o.location_id,
        l.location_name as store_name,
        extract(hour from o.ordered_at) as order_hour,
        count(*) as order_count

    from orders o
    left join locations l on o.location_id = l.location_id
    group by o.location_id, l.location_name, extract(hour from o.ordered_at)

),

store_total as (

    select
        location_id,
        sum(order_count) as total_orders

    from hourly_orders
    group by location_id

)

select
    h.location_id,
    h.store_name,
    h.order_hour,
    h.order_count,
    st.total_orders,
    round(h.order_count * 100.0 / nullif(st.total_orders, 0), 2) as pct_of_store_orders,
    case
        when h.order_hour between 6 and 9 then 'morning_commute'
        when h.order_hour between 10 and 14 then 'midday'
        when h.order_hour between 15 and 18 then 'afternoon_commute'
        when h.order_hour between 19 and 22 then 'evening'
        else 'off_hours'
    end as time_period

from hourly_orders h
left join store_total st on h.location_id = st.location_id
