with

budgets as (

    select * from {{ ref('stg_budgets') }}

),

expenses as (

    select * from {{ ref('stg_expenses') }}

),

monthly_actual as (

    select
        location_id,
        expense_category_id,
        {{ dbt.date_trunc('month', 'incurred_date') }} as expense_month,
        sum(expense_amount) as actual_spend
    from expenses
    group by 1, 2, 3

),

final as (

    select
        b.budget_id,
        b.location_id,
        b.expense_category_id,
        b.budget_month,
        b.budgeted_amount,
        coalesce(ma.actual_spend, 0) as actual_spend,
        b.budgeted_amount - coalesce(ma.actual_spend, 0) as budget_remaining,
        case
            when b.budgeted_amount > 0
                then round(coalesce(ma.actual_spend, 0) / b.budgeted_amount * 100, 2)
            else 0
        end as utilization_rate_pct,
        case
            when b.budgeted_amount > 0 and coalesce(ma.actual_spend, 0) / b.budgeted_amount > 1.0
                then 'over_budget'
            when b.budgeted_amount > 0 and coalesce(ma.actual_spend, 0) / b.budgeted_amount > 0.9
                then 'near_budget'
            when b.budgeted_amount > 0 and coalesce(ma.actual_spend, 0) / b.budgeted_amount > 0.5
                then 'on_track'
            else 'under_utilized'
        end as budget_status
    from budgets as b
    left join monthly_actual as ma
        on b.location_id = ma.location_id
        and b.expense_category_id = ma.expense_category_id
        and b.budget_month = ma.expense_month

)

select * from final
