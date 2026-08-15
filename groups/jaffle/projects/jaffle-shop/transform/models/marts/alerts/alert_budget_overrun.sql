with

budget_vs_actual as (
    select
        budget_month,
        location_id,
        expense_category_id,
        budgeted_amount,
        actual_amount,
        round((actual_amount - budgeted_amount) * 100.0 / nullif(budgeted_amount, 0), 2) as overrun_pct
    from {{ ref('int_budget_vs_actual') }}
    where actual_amount > budgeted_amount
),

alerts as (
    select
        budget_month,
        location_id,
        expense_category_id,
        budgeted_amount,
        actual_amount,
        actual_amount - budgeted_amount as overrun_amount,
        overrun_pct,
        'budget_overrun' as alert_type,
        case when overrun_pct > 25 then 'critical' else 'warning' end as severity
    from budget_vs_actual
    where overrun_pct > 10
)

select * from alerts
