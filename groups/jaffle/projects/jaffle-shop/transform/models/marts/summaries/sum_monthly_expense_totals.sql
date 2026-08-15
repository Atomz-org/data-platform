with final as (
    select
        expense_month,
        expense_category_id,
        total_expense_amount,
        expense_count,
        round(total_expense_amount * 1.0 / nullif(expense_count, 0), 2) as avg_expense_amount,
        lag(total_expense_amount) over (partition by expense_category_id order by expense_month) as prior_month_amount
    from {{ ref('int_expense_summary_monthly') }}
)
select * from final
