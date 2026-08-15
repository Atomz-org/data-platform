with

scheduled as (
    select
        location_id,
        shift_date,
        count(distinct employee_id) as scheduled_employees,
        count(*) as scheduled_shifts,
        sum(scheduled_hours) as scheduled_hours
    from {{ ref('fct_shifts') }}
    group by 1, 2
),

actual_hours as (
    select
        location_id,
        work_date as shift_date,
        sum(hours_worked) as actual_hours
    from {{ ref('fct_timecards') }}
    group by 1, 2
),

final as (
    select
        s.location_id,
        s.shift_date,
        s.scheduled_employees,
        s.scheduled_shifts,
        s.scheduled_hours as demand_hours,
        coalesce(ah.actual_hours, 0) as actual_hours_worked,
        case
            when s.scheduled_hours > 0
            then coalesce(ah.actual_hours, 0) / s.scheduled_hours * 100
            else null
        end as staffing_efficiency_pct,
        case
            when coalesce(ah.actual_hours, 0) > s.scheduled_hours * 1.15
            then 'overstaffed'
            when coalesce(ah.actual_hours, 0) < s.scheduled_hours * 0.85
            then 'understaffed'
            else 'well_staffed'
        end as staffing_status
    from scheduled as s
    left join actual_hours as ah
        on s.location_id = ah.location_id
        and s.shift_date = ah.shift_date
)

select * from final
