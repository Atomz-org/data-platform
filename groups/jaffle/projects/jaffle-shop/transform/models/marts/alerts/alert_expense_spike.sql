with

monthly_expense as (
    select
        expense_month,
        expense_category_id,
        total_expense_amount,
        avg(total_expense_amount) over (
            partition by expense_category_id order by expense_month
            rows between 3 preceding and 1 preceding
        ) as avg_3m
    from {{ ref('int_expense_summary_monthly') }}
),

alerts as (
    select
        expense_month,
        expense_category_id,
        total_expense_amount,
        avg_3m,
        round(total_expense_amount - avg_3m * 100.0 / nullif(avg_3m, 0), 2) as spike_pct,
        'expense_spike' as alert_type,
        case when total_expense_amount > avg_3m * 2 then 'critical' else 'warning' end as severity
    from monthly_expense
    where total_expense_amount > avg_3m * 1.5
      and avg_3m > 0
)

select * from alerts
