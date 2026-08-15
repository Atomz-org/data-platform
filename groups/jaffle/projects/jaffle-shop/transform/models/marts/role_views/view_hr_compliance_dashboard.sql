with

labor_compliance as (
    select * from {{ ref('rpt_labor_compliance') }}
)

select
    store_id,
    week_start,
    count(distinct employee_id) as employees_with_violations,
    count(*) as total_violations,
    case
        when count(*) = 0 then 'fully_compliant'
        when count(*) <= 2 then 'mostly_compliant'
        else 'needs_attention'
    end as compliance_status
from labor_compliance
where violation_type is not null
group by store_id, week_start
