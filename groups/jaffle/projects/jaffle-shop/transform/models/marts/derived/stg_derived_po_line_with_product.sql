with

lines as (
    select * from {{ ref('stg_po_line_items') }}
),

products as (
    select product_id, product_name from {{ ref('stg_products') }}
),

final as (
    select
        l.po_line_item_id,
        l.purchase_order_id,
        l.product_id,
        p.product_name,
        l.quantity_ordered,
        l.unit_cost,
        l.line_total
    from lines as l
    left join products as p on l.product_id = p.product_id
)

select * from final
