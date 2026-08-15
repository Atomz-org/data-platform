with invoices as (
    select total_amount from {{ ref('fct_invoices') }}
),

buckets as (
    select
        case
            when total_amount < 10 then '0-9'
            when total_amount < 50 then '10-49'
            when total_amount < 100 then '50-99'
            when total_amount < 500 then '100-499'
            else '500+'
        end as amount_bucket,
        count(*) as invoice_count,
        avg(total_amount) as avg_amount,
        min(total_amount) as min_amount,
        max(total_amount) as max_amount
    from invoices
    group by 1
)

select * from buckets
