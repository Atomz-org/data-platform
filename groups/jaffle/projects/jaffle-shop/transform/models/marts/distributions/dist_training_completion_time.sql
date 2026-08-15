with

completions as (
    select
        employee_id,
        training_course_id,
        {{ sf_datediff('day', "started_date", "completed_date") }} as completion_days
    from {{ ref('stg_training_completions') }}
    where completed_date is not null and started_date is not null
),

stats as (
    select
        round(avg(completion_days), 2) as mean_days,
        round(percentile_cont(0.50) within group (order by completion_days), 2) as median_days,
        round(percentile_cont(0.75) within group (order by completion_days), 2) as p75_days,
        round(percentile_cont(0.90) within group (order by completion_days), 2) as p90_days
    from completions
),

bucketed as (
    select
        case
            when completion_days <= 1 then 'same_day'
            when completion_days <= 7 then '1_week'
            when completion_days <= 14 then '2_weeks'
            when completion_days <= 30 then '1_month'
            else '1_month+'
        end as duration_bucket,
        count(*) as completion_count
    from completions
    group by 1
)

select b.*, s.mean_days, s.median_days, s.p75_days
from bucketed as b cross join stats as s
