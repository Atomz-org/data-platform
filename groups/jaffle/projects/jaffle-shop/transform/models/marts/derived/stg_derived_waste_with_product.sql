with

waste as (
    select * from {{ ref('stg_waste_logs') }}
),

products as (
    select product_id, product_name, product_type from {{ ref('stg_products') }}
),

final as (
    select
        w.waste_log_id,
        w.product_id,
        p.product_name,
        p.product_type,
        w.location_id,
        w.wasted_at,
        w.waste_reason,
        w.quantity_wasted,
        w.cost_of_waste
    from waste as w
    left join products as p on w.product_id = p.product_id
)

select * from final
