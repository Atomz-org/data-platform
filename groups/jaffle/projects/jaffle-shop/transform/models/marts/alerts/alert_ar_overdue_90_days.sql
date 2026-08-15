with

overdue_ar as (
    select
        invoice_id,
        customer_id,
        amount_outstanding,
        due_date,
        {{ sf_datediff('day', "due_date", "current_date") }} as days_overdue
    from {{ ref('int_accounts_receivable_aging') }}
    where {{ sf_datediff('day', "due_date", "current_date") }} > 90
),

alerts as (
    select
        invoice_id,
        customer_id,
        amount_outstanding,
        due_date,
        days_overdue,
        'ar_overdue_90_days' as alert_type,
        case
            when days_overdue > 180 then 'critical'
            when days_overdue > 120 then 'warning'
            else 'info'
        end as severity
    from overdue_ar
)

select * from alerts
