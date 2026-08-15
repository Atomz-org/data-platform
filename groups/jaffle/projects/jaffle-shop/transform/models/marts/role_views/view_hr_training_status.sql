with

training_completion as (

    select * from {{ ref('rpt_training_completion') }}

)

select
    department_name,
    total_employees,
    fully_compliant_count as total_completed,
    non_compliant_count as total_non_compliant,
    compliance_rate_pct as completion_rate_pct,
    avg_training_score as avg_score,
    case
        when compliance_rate_pct >= 95 then 'fully_compliant'
        when compliance_rate_pct >= 80 then 'mostly_compliant'
        when compliance_rate_pct >= 60 then 'partial_compliance'
        else 'non_compliant'
    end as compliance_status

from training_completion
