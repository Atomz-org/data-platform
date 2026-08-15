with

timecards as (

    select * from {{ ref('fct_timecards') }}

),

shifts as (

    select * from {{ ref('fct_shifts') }}

),

productivity as (

    select * from {{ ref('int_employee_productivity') }}

),

monthly_hours as (

    select
        employee_id,
        full_name,
        department_name,
        location_id,
        {{ dbt.date_trunc('month', 'work_date') }} as metric_month,
        sum(hours_worked) as total_hours,
        sum(net_hours_worked) as net_hours,
        sum(overtime_hours) as overtime_hours,
        count(distinct work_date) as days_worked,
        sum(break_minutes) as total_break_minutes
    from timecards
    group by 1, 2, 3, 4, 5

),

monthly_shifts as (

    select
        employee_id,
        {{ dbt.date_trunc('month', 'shift_date') }} as metric_month,
        count(distinct shift_id) as total_shifts,
        count(distinct case when is_no_show then shift_id end) as no_show_shifts,
        count(distinct case when is_late_arrival then shift_id end) as late_arrival_shifts
    from shifts
    group by 1, 2

),

monthly_productivity as (

    select
        employee_id,
        {{ dbt.date_trunc('month', 'work_date') }} as metric_month,
        sum(orders_handled) as orders_handled,
        avg(orders_per_hour) as avg_orders_per_hour
    from productivity
    group by 1, 2

),

final as (

    select
        mh.employee_id,
        mh.full_name,
        mh.department_name,
        mh.location_id,
        mh.metric_month,
        mh.total_hours,
        mh.net_hours,
        mh.overtime_hours,
        mh.days_worked,
        mh.total_break_minutes,
        round(mh.overtime_hours * 100.0 / nullif(mh.total_hours, 0), 2) as overtime_pct,

        -- Shift metrics
        coalesce(ms.total_shifts, 0) as total_shifts,
        coalesce(ms.no_show_shifts, 0) as no_show_shifts,
        coalesce(ms.late_arrival_shifts, 0) as late_arrivals,
        case
            when ms.total_shifts > 0
            then round(ms.total_shifts - coalesce(ms.no_show_shifts, 0) * 100.0 / ms.total_shifts, 2)
            else null
        end as attendance_rate_pct,

        -- Productivity
        coalesce(mp.orders_handled, 0) as orders_handled,
        round(coalesce(mp.avg_orders_per_hour, 0), 2) as avg_orders_per_hour

    from monthly_hours as mh
    left join monthly_shifts as ms
        on mh.employee_id = ms.employee_id
        and mh.metric_month = ms.metric_month
    left join monthly_productivity as mp
        on mh.employee_id = mp.employee_id
        and mh.metric_month = mp.metric_month

)

select * from final
