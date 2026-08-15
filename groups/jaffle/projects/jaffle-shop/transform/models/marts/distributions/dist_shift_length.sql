with

shifts as (
    select shift_id, scheduled_hours from {{ ref('fct_shifts') }}
    where scheduled_hours > 0
),

stats as (
    select
        round(avg(scheduled_hours), 2) as mean_length,
        round(percentile_cont(0.50) within group (order by scheduled_hours), 2) as median_length,
        round(percentile_cont(0.90) within group (order by scheduled_hours), 2) as p90_length,
        min(scheduled_hours) as min_length,
        max(scheduled_hours) as max_length
    from shifts
),

bucketed as (
    select
        case
            when scheduled_hours < 4 then 'short_(<4h)'
            when scheduled_hours < 6 then 'medium_(4-6h)'
            when scheduled_hours < 8 then 'standard_(6-8h)'
            when scheduled_hours < 10 then 'long_(8-10h)'
            else 'extended_(10h+)'
        end as length_bucket,
        count(*) as shift_count,
        round(avg(scheduled_hours), 2) as avg_hours
    from shifts
    group by 1
)

select b.*, s.mean_length, s.median_length
from bucketed as b cross join stats as s
