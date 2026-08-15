with monthly as (
    select expense_month, expense_category_id, total_expense_amount, expense_count
    from {{ ref('int_expense_summary_monthly') }}
),
final as (
    select
        {{ sf_date_trunc('quarter', "expense_month") }} as expense_quarter,
        expense_category_id,
        sum(total_expense_amount) as quarterly_amount,
        sum(expense_count) as quarterly_count,
        round(sum(total_expense_amount) * 1.0 / nullif(sum(expense_count), 0), 2) as avg_expense
    from monthly
    group by 1, 2
)
select * from final
