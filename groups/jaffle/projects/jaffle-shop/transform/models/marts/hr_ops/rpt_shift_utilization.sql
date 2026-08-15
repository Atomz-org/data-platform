with

shifts as (

    select * from {{ ref('fct_shifts') }}

),

timecards as (

    select * from {{ ref('fct_timecards') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

scheduled_by_store as (

    select
        location_id,
        location_name,
        {{ dbt.date_trunc('month', 'shift_date') }} as report_month,
        count(*) as total_shifts,
        sum(scheduled_hours) as total_scheduled_hours,
        sum(case when actual_hours is not null then actual_hours else 0 end) as total_actual_hours,
        sum(case when is_no_show then 1 else 0 end) as no_show_count,
        sum(case when is_late_arrival then 1 else 0 end) as late_arrival_count,
        count(distinct employee_id) as unique_employees

    from shifts
    group by
        location_id,
        location_name,
        {{ dbt.date_trunc('month', 'shift_date') }}

),

timecard_by_store as (

    select
        location_id,
        {{ dbt.date_trunc('month', 'work_date') }} as report_month,
        sum(hours_worked) as timecard_hours_worked,
        sum(net_hours_worked) as timecard_net_hours,
        sum(overtime_hours) as timecard_overtime_hours

    from timecards
    group by
        location_id,
        {{ dbt.date_trunc('month', 'work_date') }}

),

final as (

    select
        scheduled_by_store.location_id,
        scheduled_by_store.location_name,
        scheduled_by_store.report_month,
        scheduled_by_store.total_shifts,
        scheduled_by_store.total_scheduled_hours,
        scheduled_by_store.total_actual_hours,
        coalesce(timecard_by_store.timecard_hours_worked, 0) as timecard_hours_worked,
        coalesce(timecard_by_store.timecard_net_hours, 0) as timecard_net_hours,
        coalesce(timecard_by_store.timecard_overtime_hours, 0) as timecard_overtime_hours,
        scheduled_by_store.no_show_count,
        scheduled_by_store.late_arrival_count,
        scheduled_by_store.unique_employees,
        case
            when scheduled_by_store.total_scheduled_hours > 0
                then round(
                    (coalesce(timecard_by_store.timecard_hours_worked, 0) * 100.0
                    / scheduled_by_store.total_scheduled_hours), 1
                )
            else null
        end as utilization_pct,
        case
            when scheduled_by_store.total_shifts > 0
                then round(
                    (scheduled_by_store.no_show_count * 100.0
                    / scheduled_by_store.total_shifts), 1
                )
            else 0
        end as no_show_rate_pct,
        case
            when scheduled_by_store.total_shifts > 0
                then round(
                    (scheduled_by_store.late_arrival_count * 100.0
                    / scheduled_by_store.total_shifts), 1
                )
            else 0
        end as late_arrival_rate_pct

    from scheduled_by_store
    left join timecard_by_store
        on scheduled_by_store.location_id = timecard_by_store.location_id
        and scheduled_by_store.report_month = timecard_by_store.report_month

)

select * from final
