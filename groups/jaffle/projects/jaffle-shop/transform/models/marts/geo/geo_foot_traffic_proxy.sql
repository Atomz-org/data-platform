with

orders as (

    select * from {{ ref('stg_orders') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

hourly_traffic as (

    select
        o.location_id,
        l.location_name as store_name,
        extract(hour from o.ordered_at) as order_hour,
        {{ dbt.date_trunc('day', 'o.ordered_at') }} as order_date,
        count(*) as order_count

    from orders o
    left join locations l on o.location_id = l.location_id
    group by o.location_id, l.location_name, extract(hour from o.ordered_at), {{ dbt.date_trunc('day', 'o.ordered_at') }}

)

select
    location_id,
    store_name,
    order_hour,
    count(distinct order_date) as days_with_traffic,
    sum(order_count) as total_orders,
    round(avg(order_count), 2) as avg_daily_orders,
    max(order_count) as peak_daily_orders,
    case
        when avg(order_count) >= 20 then 'high_traffic'
        when avg(order_count) >= 10 then 'medium_traffic'
        else 'low_traffic'
    end as traffic_level

from hourly_traffic
group by location_id, store_name, order_hour
