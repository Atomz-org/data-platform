with

weekly_timecards as (
    select
        {{ sf_date_trunc('week', "work_date") }} as work_week,
        location_id,
        sum(hours_worked) as total_hours_worked,
        sum(overtime_hours) as total_overtime_hours,
        count(distinct employee_id) as active_employees
    from {{ ref('fct_timecards') }}
    group by 1, 2
),

trended as (
    select
        work_week,
        location_id,
        total_hours_worked,
        total_overtime_hours,
        total_hours_worked + total_overtime_hours as total_hours,
        active_employees,
        round(total_overtime_hours * 100.0 / nullif(total_hours_worked + total_overtime_hours, 0), 2) as overtime_pct,
        avg(total_hours_worked + total_overtime_hours) over (
            partition by location_id order by work_week
            rows between 3 preceding and current row
        ) as hours_4w_ma,
        avg(total_overtime_hours) over (
            partition by location_id order by work_week
            rows between 3 preceding and current row
        ) as overtime_4w_ma
    from weekly_timecards
)

select * from trended
