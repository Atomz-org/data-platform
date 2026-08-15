with

ar_aging as (

    select * from {{ ref('rpt_ar_aging_summary') }}

)

select
    aging_bucket,
    total_outstanding,
    receivable_count,
    customer_count,
    avg_outstanding,
    avg_days_past_due,
    pct_of_total,
    case
        when aging_bucket_sort >= 4 then 'critical'
        when aging_bucket_sort = 3 then 'warning'
        when aging_bucket_sort = 2 then 'watch'
        else 'current'
    end as collection_priority

from ar_aging
where total_outstanding > 0
