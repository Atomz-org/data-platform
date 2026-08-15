with

tenure as (
    select employee_id, tenure_days from {{ ref('int_employee_tenure') }}
),

stats as (
    select
        round(avg(tenure_days), 0) as mean_tenure,
        round(percentile_cont(0.25) within group (order by tenure_days), 0) as p25_tenure,
        round(percentile_cont(0.50) within group (order by tenure_days), 0) as median_tenure,
        round(percentile_cont(0.75) within group (order by tenure_days), 0) as p75_tenure,
        round(percentile_cont(0.90) within group (order by tenure_days), 0) as p90_tenure
    from tenure
),

bucketed as (
    select
        case
            when tenure_days < 90 then 'new_(<3m)'
            when tenure_days < 180 then 'junior_(3-6m)'
            when tenure_days < 365 then 'developing_(6-12m)'
            when tenure_days < 730 then 'experienced_(1-2y)'
            else 'veteran_(2y+)'
        end as tenure_bucket,
        count(*) as employee_count,
        round(avg(tenure_days), 0) as avg_tenure
    from tenure
    group by 1
)

select b.*, s.mean_tenure, s.median_tenure
from bucketed as b cross join stats as s
