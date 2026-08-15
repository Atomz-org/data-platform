with

purchase_orders as (

    select * from {{ ref('stg_purchase_orders') }}

),

suppliers as (

    select * from {{ ref('stg_suppliers') }}

),

po_line_items as (

    select * from {{ ref('stg_po_line_items') }}

),

line_item_summary as (

    select
        purchase_order_id,
        count(po_line_item_id) as count_line_items,
        sum(quantity_ordered) as total_quantity_ordered,
        sum(line_total) as calculated_total_amount

    from po_line_items

    group by 1

),

enriched as (

    select
        purchase_orders.purchase_order_id,
        purchase_orders.supplier_id,
        suppliers.supplier_name,
        purchase_orders.warehouse_id,
        purchase_orders.po_status,
        purchase_orders.total_amount,
        line_item_summary.count_line_items,
        line_item_summary.total_quantity_ordered,
        line_item_summary.calculated_total_amount,
        purchase_orders.ordered_at,
        purchase_orders.expected_delivery_at,
        purchase_orders.created_at

    from purchase_orders

    left join suppliers
        on purchase_orders.supplier_id = suppliers.supplier_id

    left join line_item_summary
        on purchase_orders.purchase_order_id = line_item_summary.purchase_order_id

)

select * from enriched
