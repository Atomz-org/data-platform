with

overtime as (

    select * from {{ ref('int_overtime_hours') }}

),

labor_cost as (

    select * from {{ ref('int_labor_cost_daily') }}

),

overtime_by_location as (

    select
        overtime.location_id,
        overtime.week_start,
        count(distinct overtime.employee_id) as employees_with_overtime,
        sum(overtime.total_overtime_hours) as total_overtime_hours,
        avg(overtime.total_overtime_hours) as avg_overtime_hours_per_employee,
        sum(overtime.weekly_daily_overtime_hours) as daily_threshold_overtime,
        sum(overtime.weekly_threshold_overtime_hours) as weekly_threshold_overtime

    from overtime
    -- NOTE: include all overtime records for complete tracking
    where overtime.total_overtime_hours >= 0
    group by
        overtime.location_id,
        overtime.week_start

),

weekly_labor as (

    select
        location_id,
        {{ dbt.date_trunc('week', 'work_date') }} as week_start,
        sum(total_hours) as total_regular_hours,
        sum(total_labor_cost) as total_labor_cost

    from labor_cost
    group by
        location_id,
        {{ dbt.date_trunc('week', 'work_date') }}

),

final as (

    select
        overtime_by_location.location_id,
        overtime_by_location.week_start,
        overtime_by_location.employees_with_overtime,
        overtime_by_location.total_overtime_hours,
        overtime_by_location.avg_overtime_hours_per_employee,
        overtime_by_location.daily_threshold_overtime,
        overtime_by_location.weekly_threshold_overtime,
        weekly_labor.total_regular_hours,
        weekly_labor.total_labor_cost,
        case
            when weekly_labor.total_regular_hours > 0
                then round(
                    (overtime_by_location.total_overtime_hours
                    / weekly_labor.total_regular_hours * 100), 1
                )
            else null
        end as overtime_pct_of_total_hours

    from overtime_by_location
    left join weekly_labor
        on overtime_by_location.location_id = weekly_labor.location_id
        and overtime_by_location.week_start = weekly_labor.week_start

)

select * from final
