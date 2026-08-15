with

pli as (
    select * from {{ ref('stg_po_line_items') }}
),

line_items as (

    select
        pli.po_line_item_id,
        pli.purchase_order_id,
        pli.product_id,
        pli.quantity_ordered,
        pli.unit_cost,
        pli.line_total
    from pli

),

size_buckets as (

    select
        product_id,
        case
            when quantity_ordered >= 100 then 'bulk'
            when quantity_ordered >= 50 then 'medium'
            else 'small'
        end as order_size_bucket,
        quantity_ordered,
        unit_cost,
        line_total
    from line_items

),

bucket_summary as (

    select
        product_id,
        order_size_bucket,
        count(*) as order_count,
        avg(unit_cost) as avg_unit_cost,
        sum(quantity_ordered) as total_quantity,
        sum(line_total) as total_spend
    from size_buckets
    group by 1, 2

),

with_small_baseline as (

    select
        bs.*,
        small.avg_unit_cost as small_order_avg_cost,
        case
            when small.avg_unit_cost > 0
            then (small.avg_unit_cost - bs.avg_unit_cost) / small.avg_unit_cost * 100
            else 0
        end as savings_vs_small_pct,
        (small.avg_unit_cost - bs.avg_unit_cost) * bs.total_quantity as total_savings_vs_small
    from bucket_summary as bs
    left join bucket_summary as small
        on bs.product_id = small.product_id
        and small.order_size_bucket = 'small'

)

select * from with_small_baseline
