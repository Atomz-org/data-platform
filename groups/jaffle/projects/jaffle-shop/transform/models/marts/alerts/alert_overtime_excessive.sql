with

weekly_hours as (
    select
        {{ sf_date_trunc('week', "work_date") }} as work_week,
        employee_id,
        location_id,
        sum(hours_worked) as hours_worked,
        sum(overtime_hours) as overtime_hours,
        sum(hours_worked + overtime_hours) as total_hours
    from {{ ref('fct_timecards') }}
    group by 1, 2, 3
),

alerts as (
    select
        work_week,
        employee_id,
        location_id,
        hours_worked,
        overtime_hours,
        total_hours,
        round(overtime_hours * 100.0 / nullif(total_hours, 0), 2) as overtime_pct,
        'overtime_excessive' as alert_type,
        case when overtime_hours > 20 then 'critical' else 'warning' end as severity
    from weekly_hours
    where overtime_hours * 100.0 / nullif(total_hours, 0) > 20
)

select * from alerts
