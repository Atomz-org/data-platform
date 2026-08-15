with

budget_vs_actual as (

    select * from {{ ref('int_budget_vs_actual') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

final as (

    select
        bva.budget_id,
        bva.location_id,
        l.location_name,
        bva.expense_category_id,
        bva.budget_type,
        bva.budget_month,
        bva.budgeted_amount,
        bva.actual_amount,
        bva.variance_amount,
        bva.variance_pct,
        case
            when bva.budget_type = 'revenue' and bva.variance_amount >= 0 then 'favorable'
            when bva.budget_type = 'revenue' and bva.variance_amount < 0 then 'unfavorable'
            when bva.budget_type = 'expense' and bva.variance_amount <= 0 then 'favorable'
            when bva.budget_type = 'expense' and bva.variance_amount > 0 then 'unfavorable'
        end as variance_status,
        case
            when abs(bva.variance_pct) > 0.20 then 'critical'
            when abs(bva.variance_pct) > 0.10 then 'warning'
            else 'on_track'
        end as variance_severity

    from budget_vs_actual as bva
    left join locations as l
        on bva.location_id = l.location_id

)

select * from final
