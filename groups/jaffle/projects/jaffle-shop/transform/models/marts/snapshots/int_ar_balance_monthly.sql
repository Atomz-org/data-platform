with

ar_aging as (

    select * from {{ ref('int_accounts_receivable_aging') }}

),

-- Snapshot AR balances grouped by month based on creation date
monthly_ar as (

    select
        {{ dbt.date_trunc('month', 'created_date') }} as month_start,
        count(receivable_id) as open_receivables,
        sum(amount_due) as total_amount_due,
        sum(amount_paid) as total_amount_paid,
        sum(amount_outstanding) as total_outstanding,
        avg(amount_outstanding) as avg_outstanding_per_receivable,
        sum(
            case when aging_bucket = 'current' then amount_outstanding else 0 end
        ) as outstanding_current,
        sum(
            case when aging_bucket = '1-30 days' then amount_outstanding else 0 end
        ) as outstanding_1_30,
        sum(
            case when aging_bucket = '31-60 days' then amount_outstanding else 0 end
        ) as outstanding_31_60,
        sum(
            case when aging_bucket = '61-90 days' then amount_outstanding else 0 end
        ) as outstanding_61_90,
        sum(
            case when aging_bucket = '90+ days' then amount_outstanding else 0 end
        ) as outstanding_90_plus

    from ar_aging
    group by 1

)

select * from monthly_ar
