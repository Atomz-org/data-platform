with

shift_coverage as (
    select
        shift_date,
        location_id,
        count(*) as scheduled_shifts,
        count(case when shift_status = 'completed' then 1 end) as completed_shifts,
        count(case when shift_status = 'no_show' then 1 end) as no_show_shifts
    from {{ ref('fct_shifts') }}
    group by 1, 2
),

alerts as (
    select
        shift_date,
        location_id,
        scheduled_shifts,
        completed_shifts,
        no_show_shifts,
        round(no_show_shifts * 100.0 / nullif(scheduled_shifts, 0), 2) as no_show_pct,
        'understaffed_shift' as alert_type,
        case when no_show_shifts >= 3 then 'critical' else 'warning' end as severity
    from shift_coverage
    where no_show_shifts > 0
      and no_show_shifts * 100.0 / nullif(scheduled_shifts, 0) > 15
)

select * from alerts
