with

scheduling as (

    select * from {{ ref('rpt_scheduling_optimization') }}

),

employees as (

    select * from {{ ref('dim_employees') }}

),

staffing as (

    select
        s.location_id,
        s.report_week,
        s.total_weekly_scheduled_hours,
        s.total_weekly_orders,
        s.avg_orders_per_staff,
        count(distinct e.employee_id) as active_employees

    from scheduling s
    left join employees e on s.location_id = e.location_id and e.is_active = true
    group by s.location_id, s.report_week, s.total_weekly_scheduled_hours, s.total_weekly_orders, s.avg_orders_per_staff

)

select
    location_id,
    report_week,
    total_weekly_scheduled_hours,
    total_weekly_orders,
    avg_orders_per_staff,
    active_employees,
    round(total_weekly_orders - total_weekly_scheduled_hours, 2) as hours_variance,
    case
        when avg_orders_per_staff < 80 then 'understaffed'
        when avg_orders_per_staff > 120 then 'overstaffed'
        else 'adequately_staffed'
    end as staffing_status

from staffing
