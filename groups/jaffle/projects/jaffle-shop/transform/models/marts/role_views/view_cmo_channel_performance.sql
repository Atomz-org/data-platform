with

channel_attribution as (
    select * from {{ ref('rpt_channel_attribution') }}
)

select
    channel,
    total_revenue as attributed_revenue,
    total_spend as channel_spend,
    customers_acquired as attributed_customers,
    round(total_revenue / nullif(total_spend, 0), 2) as roas,
    cost_per_acquisition
from channel_attribution
