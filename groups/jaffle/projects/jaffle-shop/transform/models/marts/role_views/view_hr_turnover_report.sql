with

turnover as (
    select * from {{ ref('rpt_employee_turnover') }}
)

select
    tenure_bucket,
    employee_count as headcount,
    active_count,
    terminated_count as terminations,
    turnover_rate_pct,
    case
        when turnover_rate_pct > 20 then 'critical'
        when turnover_rate_pct > 10 then 'high'
        when turnover_rate_pct > 5 then 'moderate'
        else 'healthy'
    end as turnover_severity
from turnover
