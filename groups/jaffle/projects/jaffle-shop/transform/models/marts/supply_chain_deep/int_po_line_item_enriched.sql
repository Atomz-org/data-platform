with

po_items as (

    select * from {{ ref('stg_po_line_items') }}

),

pos as (

    select
        purchase_order_id,
        supplier_id,
        po_status,
        ordered_at
    from {{ ref('stg_purchase_orders') }}

),

suppliers as (

    select
        supplier_id,
        supplier_name
    from {{ ref('stg_suppliers') }}

),

products as (

    select
        product_id,
        product_name,
        product_type
    from {{ ref('stg_products') }}

),

final as (

    select
        pi.po_line_item_id,
        pi.purchase_order_id,
        pi.product_id,
        p.product_name,
        p.product_type,
        po.supplier_id,
        s.supplier_name,
        po.po_status,
        po.ordered_at,
        pi.quantity_ordered,
        pi.unit_cost,
        pi.line_total
    from po_items as pi
    inner join pos as po
        on pi.purchase_order_id = po.purchase_order_id
    left join suppliers as s
        on po.supplier_id = s.supplier_id
    left join products as p
        on pi.product_id = p.product_id

)

select * from final
