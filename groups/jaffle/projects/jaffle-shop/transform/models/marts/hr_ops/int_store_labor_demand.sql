with

orders as (

    select * from {{ ref('stg_orders') }}

),

labor_hours as (

    select * from {{ ref('int_labor_hours_actual') }}

),

daily_order_volume as (

    select
        location_id,
        ordered_at as order_date,
        count(*) as order_count,
        sum(order_total) as daily_revenue,
        {{ day_of_week_number('ordered_at') }} as day_of_week,
        case {{ day_of_week_number('ordered_at') }}
            when 0 then 'Sunday'
            when 1 then 'Monday'
            when 2 then 'Tuesday'
            when 3 then 'Wednesday'
            when 4 then 'Thursday'
            when 5 then 'Friday'
            when 6 then 'Saturday'
        end as day_name,
        {{ dbt.date_trunc('month', 'ordered_at') }} as order_month

    from orders
    group by
        location_id,
        ordered_at

),

daily_labor as (

    select
        location_id,
        work_date,
        sum(total_hours_worked) as total_labor_hours,
        count(distinct employee_id) as staff_count

    from labor_hours
    group by
        location_id,
        work_date

),

demand_with_labor as (

    select
        daily_order_volume.location_id,
        daily_order_volume.order_date,
        daily_order_volume.day_of_week,
        daily_order_volume.day_name,
        daily_order_volume.order_month,
        daily_order_volume.order_count,
        daily_order_volume.daily_revenue,
        coalesce(daily_labor.total_labor_hours, 0) as actual_labor_hours,
        coalesce(daily_labor.staff_count, 0) as actual_staff_count,
        case
            when coalesce(daily_labor.total_labor_hours, 0) > 0
                then round(
                    (daily_order_volume.order_count * 1.0
                    / daily_labor.total_labor_hours), 2
                )
            else null
        end as orders_per_labor_hour

    from daily_order_volume
    left join daily_labor
        on daily_order_volume.location_id = daily_labor.location_id
        and daily_order_volume.order_date = daily_labor.work_date

),

avg_demand_by_dow as (

    select
        location_id,
        day_of_week,
        day_name,
        avg(order_count) as avg_daily_orders,
        avg(actual_labor_hours) as avg_labor_hours,
        avg(actual_staff_count) as avg_staff_count,
        avg(orders_per_labor_hour) as avg_orders_per_labor_hour,
        case
            when avg(orders_per_labor_hour) > 0
                then round(avg(order_count) / avg(orders_per_labor_hour), 1)
            else null
        end as predicted_labor_hours_needed

    from demand_with_labor
    group by
        location_id,
        day_of_week,
        day_name

)

select * from avg_demand_by_dow
