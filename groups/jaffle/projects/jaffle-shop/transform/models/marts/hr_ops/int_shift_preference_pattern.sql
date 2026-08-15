with

shifts as (

    select * from {{ ref('stg_shifts') }}

),

employees as (

    select * from {{ ref('stg_employees') }}

),

shift_patterns as (

    select
        shifts.location_id,
        shifts.shift_type,
        {{ day_of_week_number('shifts.shift_date') }} as day_of_week,
        case {{ day_of_week_number('shifts.shift_date') }}
            when 0 then 'Sunday'
            when 1 then 'Monday'
            when 2 then 'Tuesday'
            when 3 then 'Wednesday'
            when 4 then 'Thursday'
            when 5 then 'Friday'
            when 6 then 'Saturday'
        end as day_name,
        count(distinct shifts.shift_id) as shift_count,
        count(distinct shifts.employee_id) as unique_employees,
        sum(case when shifts.shift_status = 'no_show' then 1 else 0 end) as no_show_count,
        sum(case when shifts.shift_status = 'completed' then 1 else 0 end) as completed_count,
        case
            when count(*) > 0
                then round(
                    (sum(case when shifts.shift_status = 'no_show' then 1 else 0 end) * 100.0
                    / count(*)), 1
                )
            else 0
        end as no_show_rate_pct

    from shifts
    inner join employees
        on shifts.employee_id = employees.employee_id
    group by
        shifts.location_id,
        shifts.shift_type,
        {{ day_of_week_number('shifts.shift_date') }}

),

ranked as (

    select
        location_id,
        shift_type,
        day_of_week,
        day_name,
        shift_count,
        unique_employees,
        no_show_count,
        completed_count,
        no_show_rate_pct,
        rank() over (
            partition by location_id
            order by shift_count desc
        ) as popularity_rank,
        rank() over (
            partition by location_id
            order by no_show_rate_pct desc
        ) as worst_attendance_rank

    from shift_patterns

)

select * from ranked
