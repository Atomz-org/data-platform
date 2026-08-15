with

shift_coverage as (

    select * from {{ ref('int_shift_coverage') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

daily_orders as (

    select
        location_id,
        ordered_at as order_date,
        count(*) as order_count

    from orders
    group by
        location_id,
        ordered_at

),

staffing_ratio as (

    select
        shift_coverage.location_id,
        shift_coverage.location_name,
        shift_coverage.shift_date,
        shift_coverage.scheduled_staff_count,
        shift_coverage.total_scheduled_hours,
        coalesce(daily_orders.order_count, 0) as order_count,
        case
            when coalesce(daily_orders.order_count, 0) > 0
                then round(shift_coverage.total_scheduled_hours / daily_orders.order_count, 2)
            else null
        end as staff_hours_per_order,
        case
            when shift_coverage.scheduled_staff_count > 0
                then round(coalesce(daily_orders.order_count, 0) * 1.0 / shift_coverage.scheduled_staff_count, 1)
            else null
        end as orders_per_staff

    from shift_coverage
    left join daily_orders
        on shift_coverage.location_id = daily_orders.location_id
        and shift_coverage.shift_date = daily_orders.order_date

)

select * from staffing_ratio
