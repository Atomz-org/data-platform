with

refunds as (
    select refund_id, refund_amount from {{ ref('fct_refunds') }}
    where refund_amount > 0
),

stats as (
    select
        count(*) as total_refunds,
        round(avg(refund_amount), 2) as mean_refund,
        round(percentile_cont(0.50) within group (order by refund_amount), 2) as median_refund,
        round(percentile_cont(0.75) within group (order by refund_amount), 2) as p75_refund,
        round(percentile_cont(0.90) within group (order by refund_amount), 2) as p90_refund,
        round(percentile_cont(0.95) within group (order by refund_amount), 2) as p95_refund
    from refunds
),

bucketed as (
    select
        case
            when refund_amount < 5 then '0-5'
            when refund_amount < 10 then '5-10'
            when refund_amount < 25 then '10-25'
            when refund_amount < 50 then '25-50'
            else '50+'
        end as refund_bucket,
        count(*) as refund_count,
        round(sum(refund_amount), 2) as bucket_total
    from refunds
    group by 1
)

select b.*, s.mean_refund, s.median_refund, s.p90_refund, s.total_refunds
from bucketed as b cross join stats as s
