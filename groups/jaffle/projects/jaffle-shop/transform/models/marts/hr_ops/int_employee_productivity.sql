with

labor_hours as (

    select * from {{ ref('int_labor_hours_actual') }}

),

shifts as (

    select * from {{ ref('stg_shifts') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

orders_during_shifts as (

    select
        shifts.employee_id,
        shifts.location_id,
        shifts.shift_date,
        count(distinct orders.order_id) as orders_handled

    from shifts
    inner join orders
        on shifts.location_id = orders.location_id
        and orders.ordered_at = shifts.shift_date
        and shifts.shift_status != 'no_show'
    group by
        shifts.employee_id,
        shifts.location_id,
        shifts.shift_date

),

productivity as (

    select
        labor_hours.employee_id,
        labor_hours.location_id,
        labor_hours.work_date,
        labor_hours.total_hours_worked,
        coalesce(orders_during_shifts.orders_handled, 0) as orders_handled,
        case
            when labor_hours.total_hours_worked > 0
                then round(
                    (coalesce(orders_during_shifts.orders_handled, 0) * 1.0
                    / labor_hours.total_hours_worked), 2
                )
            else 0
        end as orders_per_hour,
        case
            when coalesce(orders_during_shifts.orders_handled, 0) > 0
                then round(
                    (labor_hours.total_hours_worked
                    / orders_during_shifts.orders_handled), 2
                )
            else null
        end as hours_per_order

    from labor_hours
    left join orders_during_shifts
        on labor_hours.employee_id = orders_during_shifts.employee_id
        and labor_hours.location_id = orders_during_shifts.location_id
        and labor_hours.work_date = orders_during_shifts.shift_date

)

select * from productivity
