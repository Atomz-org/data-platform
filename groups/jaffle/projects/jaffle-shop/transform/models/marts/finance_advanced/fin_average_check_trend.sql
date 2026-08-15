with

orders as (

    select
        order_id,
        location_id,
        order_total,
        {{ dbt.date_trunc('week', 'ordered_at') }} as order_week,
        {{ dbt.date_trunc('month', 'ordered_at') }} as order_month
    from {{ ref('stg_orders') }}

),

store_names as (

    select location_id, location_name as store_name
    from {{ ref('stg_locations') }}

),

weekly_avg as (

    select
        o.location_id,
        s.store_name,
        o.order_week,
        count(o.order_id) as weekly_orders,
        avg(o.order_total) as avg_check_size,
        min(o.order_total) as min_check_size,
        max(o.order_total) as max_check_size
    from orders as o
    inner join store_names as s on o.location_id = s.location_id
    group by 1, 2, 3

),

with_trend as (

    select
        location_id,
        store_name,
        order_week,
        weekly_orders,
        avg_check_size,
        min_check_size,
        max_check_size,
        lag(avg_check_size, 4) over (
            partition by location_id order by order_week
        ) as avg_check_4_weeks_ago,
        avg(avg_check_size) over (
            partition by location_id order by order_week
            rows between 3 preceding and current row
        ) as avg_check_4_week_moving_avg
    from weekly_avg

)

select
    location_id,
    store_name,
    order_week,
    weekly_orders,
    avg_check_size,
    min_check_size,
    max_check_size,
    avg_check_4_week_moving_avg,
    case
        when avg_check_4_weeks_ago > 0
        then (avg_check_size - avg_check_4_weeks_ago) / avg_check_4_weeks_ago * 100
        else null
    end as check_size_growth_pct_4w
from with_trend
