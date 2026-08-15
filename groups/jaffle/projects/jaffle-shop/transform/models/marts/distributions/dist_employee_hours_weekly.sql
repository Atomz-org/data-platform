with

weekly_hours as (
    select
        employee_id,
        {{ sf_date_trunc('week', "work_date") }} as work_week,
        sum(hours_worked + overtime_hours) as total_hours
    from {{ ref('fct_timecards') }}
    group by 1, 2
),

stats as (
    select
        round(avg(total_hours), 2) as mean_hours,
        round(percentile_cont(0.25) within group (order by total_hours), 2) as p25,
        round(percentile_cont(0.50) within group (order by total_hours), 2) as p50,
        round(percentile_cont(0.75) within group (order by total_hours), 2) as p75,
        round(percentile_cont(0.90) within group (order by total_hours), 2) as p90
    from weekly_hours
),

bucketed as (
    select
        case
            when total_hours < 20 then 'part_time_low'
            when total_hours < 32 then 'part_time'
            when total_hours < 40 then 'near_full_time'
            when total_hours = 40 then 'full_time'
            else 'overtime'
        end as hours_bucket,
        count(*) as week_count,
        round(avg(total_hours), 2) as avg_hours
    from weekly_hours
    group by 1
)

select b.*, s.mean_hours, s.p50, s.p75, s.p90
from bucketed as b cross join stats as s
