with

monthly_expense as (
    select
        expense_month,
        expense_category_id,
        total_expense_amount,
        expense_count
    from {{ ref('int_expense_summary_monthly') }}
),

compared as (
    select
        expense_month,
        expense_category_id,
        total_expense_amount as current_amount,
        lag(total_expense_amount) over (partition by expense_category_id order by expense_month) as prior_month_amount,
        expense_count as current_count,
        lag(expense_count) over (partition by expense_category_id order by expense_month) as prior_month_count,
        round(((total_expense_amount - lag(total_expense_amount) over (partition by expense_category_id order by expense_month))) * 100.0
            / nullif(lag(total_expense_amount) over (partition by expense_category_id order by expense_month), 0), 2) as expense_mom_pct
    from monthly_expense
)

select * from compared
