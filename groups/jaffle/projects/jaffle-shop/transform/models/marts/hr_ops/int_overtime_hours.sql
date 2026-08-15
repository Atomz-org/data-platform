with

labor_hours as (

    select * from {{ ref('int_labor_hours_actual') }}

),

daily_overtime as (

    select
        employee_id,
        location_id,
        work_date,
        total_hours_worked,
        case
            when total_hours_worked > 8 then total_hours_worked - 8
            else 0
        end as daily_overtime_hours

    from labor_hours

),

weekly_hours as (

    select
        employee_id,
        location_id,
        {{ dbt.date_trunc('week', 'work_date') }} as week_start,
        sum(total_hours_worked) as weekly_total_hours,
        sum(daily_overtime_hours) as weekly_daily_overtime_hours

    from daily_overtime
    group by
        employee_id,
        location_id,
        {{ dbt.date_trunc('week', 'work_date') }}

),

final as (

    select
        employee_id,
        location_id,
        week_start,
        weekly_total_hours,
        weekly_daily_overtime_hours,
        case
            when weekly_total_hours > 40 then weekly_total_hours - 40
            else 0
        end as weekly_threshold_overtime_hours,
        {{ sf_greatest(["weekly_daily_overtime_hours", "(case when weekly_total_hours > 40 then weekly_total_hours - 40 else 0 end)"]) }} as total_overtime_hours

    from weekly_hours

)

select * from final
