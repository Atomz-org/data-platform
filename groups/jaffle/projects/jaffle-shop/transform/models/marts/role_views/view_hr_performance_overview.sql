with

performance as (
    select * from {{ ref('scr_employee_performance') }}
)

select
    employee_id,
    performance_score,
    productivity_score,
    attendance_score,
    training_score,
    performance_tier,
    case
        when performance_score >= 90 then 'exceptional'
        when performance_score >= 75 then 'above_average'
        when performance_score >= 60 then 'meets_expectations'
        when performance_score >= 40 then 'below_expectations'
        else 'needs_improvement'
    end as performance_band,
    percent_rank() over (order by performance_score) as performance_percentile
from performance
