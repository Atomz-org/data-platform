with

budget_vs_actual as (

    select * from {{ ref('int_budget_vs_actual') }}

)

select
    budget_month,
    location_id,
    expense_category_id,
    budgeted_amount,
    actual_amount,
    variance_amount,
    variance_pct,
    case
        when variance_pct > 10 then 'significantly_over_budget'
        when variance_pct > 0 then 'over_budget'
        when variance_pct >= -10 then 'under_budget'
        else 'significantly_under_budget'
    end as budget_status

from budget_vs_actual
