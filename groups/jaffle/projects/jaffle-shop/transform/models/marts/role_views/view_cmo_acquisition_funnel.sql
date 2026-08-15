with

acquisition_funnel as (
    select * from {{ ref('rpt_customer_acquisition_funnel') }}
)

select
    acquisition_source,
    total_customers as customer_count,
    source_share,
    source_rank,
    round(total_customers * 100.0 / nullif(sum(total_customers) over (), 0), 2) as pct_of_total
from acquisition_funnel
