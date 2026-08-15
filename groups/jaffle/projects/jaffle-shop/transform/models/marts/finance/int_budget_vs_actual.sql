with

budgets as (

    select * from {{ ref('stg_budgets') }}

),

monthly_revenue as (

    select
        location_id,
        {{ dbt.date_trunc('month', 'revenue_date') }} as revenue_month,
        sum(total_revenue) as actual_revenue

    from {{ ref('int_daily_revenue') }}
    group by 1, 2

),

monthly_expenses as (

    select
        location_id,
        expense_category_id,
        expense_month,
        total_expense_amount as actual_expense

    from {{ ref('int_expense_summary_monthly') }}

),

revenue_budget_vs_actual as (

    select
        b.budget_id,
        b.location_id,
        b.expense_category_id,
        b.budget_type,
        b.budget_month,
        b.budgeted_amount,
        coalesce(mr.actual_revenue, 0) as actual_amount,
        coalesce(mr.actual_revenue, 0) - b.budgeted_amount as variance_amount,
        case
            when b.budgeted_amount != 0
                then (coalesce(mr.actual_revenue, 0) - b.budgeted_amount)
                    / b.budgeted_amount
            else 0
        end as variance_pct

    from budgets as b
    left join monthly_revenue as mr
        on b.location_id = mr.location_id
        and b.budget_month = mr.revenue_month
    where b.budget_type = 'revenue'

),

expense_budget_vs_actual as (

    select
        b.budget_id,
        b.location_id,
        b.expense_category_id,
        b.budget_type,
        b.budget_month,
        b.budgeted_amount,
        coalesce(me.actual_expense, 0) as actual_amount,
        coalesce(me.actual_expense, 0) - b.budgeted_amount as variance_amount,
        case
            when b.budgeted_amount != 0
                then (coalesce(me.actual_expense, 0) - b.budgeted_amount)
                    / b.budgeted_amount
            else 0
        end as variance_pct

    from budgets as b
    left join monthly_expenses as me
        on b.location_id = me.location_id
        and b.expense_category_id = me.expense_category_id
        and b.budget_month = me.expense_month
    where b.budget_type = 'expense'

),

combined as (

    select * from revenue_budget_vs_actual
    union all
    select * from expense_budget_vs_actual

)

select * from combined
