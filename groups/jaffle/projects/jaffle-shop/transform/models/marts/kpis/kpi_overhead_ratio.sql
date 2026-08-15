with rev as (
    select month_start, sum(monthly_revenue) as monthly_revenue
    from {{ ref('met_monthly_revenue_by_store') }}
    group by 1
),
overhead as (
    select expense_month, sum(total_expense_amount) as overhead_cost
    from {{ ref('int_expense_summary_monthly') }}
    group by 1
),
final as (
    select
        r.month_start,
        coalesce(o.overhead_cost, 0) as overhead_cost,
        r.monthly_revenue,
        round(coalesce(o.overhead_cost, 0) * 100.0 / nullif(r.monthly_revenue, 0), 2) as overhead_ratio
    from rev as r
    left join overhead as o on r.month_start = o.expense_month
)
select * from final
