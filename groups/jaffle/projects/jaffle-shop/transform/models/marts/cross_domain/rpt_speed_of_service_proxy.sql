with

t as (
    select * from {{ ref('stg_timecards') }}
),

hourly_orders as (
    select
        store_id,
        order_hour,
        avg_orders_per_hour,
        total_orders_in_hour,
        days_with_data
    from {{ ref('int_order_throughput_by_hour') }}
),

timecard_hours as (
    select
        t.location_id as store_id,
        extract(hour from t.clock_in) as shift_start_hour,
        sum(t.hours_worked) as total_hours_in_slot,
        count(distinct t.employee_id) as employees_present
    from t
    group by t.location_id, extract(hour from t.clock_in)
),

combined as (
    select
        ho.store_id,
        ho.order_hour,
        ho.avg_orders_per_hour,
        ho.total_orders_in_hour,
        ho.days_with_data,
        coalesce(th.employees_present, 1) as employees_present,
        coalesce(th.total_hours_in_slot, 1) as labor_hours_in_slot,
        round(
            (cast(ho.avg_orders_per_hour as {{ dbt.type_float() }})
            / nullif(th.employees_present, 0)), 2
        ) as orders_per_employee_per_hour,
        round(
            (cast(60.0 as {{ dbt.type_float() }})
            * nullif(th.employees_present, 0)
            / nullif(ho.avg_orders_per_hour, 0)), 2
        ) as est_minutes_per_order
    from hourly_orders as ho
    left join timecard_hours as th
        on ho.store_id = th.store_id
        and ho.order_hour = th.shift_start_hour
),

store_names as (
    select location_id as store_id, location_name as store_name
    from {{ ref('stg_locations') }}
)

select
    sn.store_name,
    c.store_id,
    c.order_hour,
    c.avg_orders_per_hour,
    c.employees_present,
    c.orders_per_employee_per_hour,
    c.est_minutes_per_order,

    -- Store-level averages for comparison
    avg(c.orders_per_employee_per_hour) over (partition by c.store_id) as store_avg_orders_per_emp_hr,
    avg(c.est_minutes_per_order) over (partition by c.store_id) as store_avg_minutes_per_order,

    -- Fleet averages
    avg(c.orders_per_employee_per_hour) over () as fleet_avg_orders_per_emp_hr,
    avg(c.est_minutes_per_order) over () as fleet_avg_minutes_per_order,

    case
        when c.orders_per_employee_per_hour >
            avg(c.orders_per_employee_per_hour) over (partition by c.store_id) * 1.2
            then 'high_throughput'
        when c.orders_per_employee_per_hour <
            avg(c.orders_per_employee_per_hour) over (partition by c.store_id) * 0.8
            then 'low_throughput'
        else 'normal_throughput'
    end as throughput_classification

from combined as c
left join store_names as sn
    on c.store_id = sn.store_id
