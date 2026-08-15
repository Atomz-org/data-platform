with

pos as (
    select purchase_order_id, total_amount from {{ ref('fct_purchase_orders') }}
    where total_amount > 0
),

stats as (
    select
        count(*) as total_pos,
        round(avg(total_amount), 2) as mean_value,
        round(percentile_cont(0.50) within group (order by total_amount), 2) as median_value,
        round(percentile_cont(0.75) within group (order by total_amount), 2) as p75_value,
        round(percentile_cont(0.90) within group (order by total_amount), 2) as p90_value
    from pos
),

bucketed as (
    select
        case
            when total_amount < 100 then 'small_(<100)'
            when total_amount < 500 then 'medium_(100-500)'
            when total_amount < 1000 then 'large_(500-1000)'
            else 'very_large_(1000+)'
        end as value_bucket,
        count(*) as po_count,
        round(sum(total_amount), 2) as bucket_total
    from pos
    group by 1
)

select b.*, s.mean_value, s.median_value, s.total_pos
from bucketed as b cross join stats as s
