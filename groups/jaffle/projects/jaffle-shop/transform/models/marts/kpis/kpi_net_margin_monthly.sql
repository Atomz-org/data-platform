with rev as (
    select month_start, sum(monthly_revenue) as monthly_revenue
    from {{ ref('met_monthly_revenue_by_store') }}
    group by 1
),
expenses as (
    select expense_month, sum(total_expense_amount) as total_expenses
    from {{ ref('int_expense_summary_monthly') }}
    group by 1
),
final as (
    select
        r.month_start,
        r.monthly_revenue,
        coalesce(e.total_expenses, 0) as total_expenses,
        r.monthly_revenue - coalesce(e.total_expenses, 0) as net_income,
        round((r.monthly_revenue - coalesce(e.total_expenses, 0)) * 100.0 / nullif(r.monthly_revenue, 0), 2) as net_margin_pct
    from rev as r
    left join expenses as e on r.month_start = e.expense_month
)
select * from final
