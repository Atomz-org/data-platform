with

ar_aging as (

    select * from {{ ref('int_accounts_receivable_aging') }}

),

customers as (

    select * from {{ ref('stg_customers') }}

),

aging_summary as (

    select
        ar.aging_bucket,
        ar.aging_bucket_sort,
        count(ar.receivable_id) as receivable_count,
        count(distinct ar.customer_id) as customer_count,
        sum(ar.amount_outstanding) as total_outstanding,
        avg(ar.amount_outstanding) as avg_outstanding,
        min(ar.amount_outstanding) as min_outstanding,
        max(ar.amount_outstanding) as max_outstanding,
        avg(ar.days_past_due) as avg_days_past_due

    from ar_aging as ar
    group by 1, 2

),

with_totals as (

    select
        aging_bucket,
        aging_bucket_sort,
        receivable_count,
        customer_count,
        total_outstanding,
        avg_outstanding,
        min_outstanding,
        max_outstanding,
        avg_days_past_due,
        sum(total_outstanding) over () as grand_total_outstanding,
        case
            when sum(total_outstanding) over () > 0
                then total_outstanding / sum(total_outstanding) over ()
            else 0
        end as pct_of_total

    from aging_summary

)

select * from with_totals
order by aging_bucket_sort
