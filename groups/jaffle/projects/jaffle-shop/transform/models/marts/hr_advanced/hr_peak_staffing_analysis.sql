with

timecards as (

    select
        employee_id,
        location_id,
        clock_in,
        extract(hour from clock_in) as clock_in_hour,
        hours_worked
    from {{ ref('fct_timecards') }}

),

orders_by_hour as (

    select
        location_id,
        extract(hour from ordered_at) as order_hour,
        {{ dbt.date_trunc('day', 'ordered_at') }} as order_date,
        count(*) as hourly_orders,
        sum(order_total) as hourly_revenue
    from {{ ref('stg_orders') }}
    group by 1, 2, 3

),

avg_demand_by_hour as (

    select
        location_id,
        order_hour,
        avg(hourly_orders) as avg_hourly_orders,
        avg(hourly_revenue) as avg_hourly_revenue
    from orders_by_hour
    group by 1, 2

),

staff_by_hour as (

    select
        location_id,
        clock_in_hour,
        count(distinct employee_id) as avg_staff_on_hand
    from timecards
    group by 1, 2

),

final as (

    select
        d.location_id,
        d.order_hour,
        d.avg_hourly_orders,
        d.avg_hourly_revenue,
        coalesce(s.avg_staff_on_hand, 0) as staff_count,
        case
            when coalesce(s.avg_staff_on_hand, 0) > 0
            then d.avg_hourly_orders / s.avg_staff_on_hand
            else null
        end as orders_per_staff,
        case
            when d.avg_hourly_orders > (select avg(avg_hourly_orders) * 1.3 from avg_demand_by_hour)
            then 'peak'
            when d.avg_hourly_orders < (select avg(avg_hourly_orders) * 0.7 from avg_demand_by_hour)
            then 'off_peak'
            else 'normal'
        end as demand_period
    from avg_demand_by_hour as d
    left join staff_by_hour as s
        on d.location_id = s.location_id
        and d.order_hour = s.clock_in_hour

)

select * from final
