with order_item_counts as (

    select
        order_id,
        count(*) as item_count
    from {{ ref('stg_order_items') }}
    group by order_id

)

select
    avg(item_count) as avg_items,
    percentile_cont(0.5) within group (order by item_count) as median_items
from order_item_counts
