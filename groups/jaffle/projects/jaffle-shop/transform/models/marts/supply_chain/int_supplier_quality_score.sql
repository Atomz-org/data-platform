with

po_receipts as (

    select * from {{ ref('stg_po_receipts') }}

),

po_line_items as (

    select * from {{ ref('stg_po_line_items') }}

),

purchase_orders as (

    select * from {{ ref('stg_purchase_orders') }}

),

waste_logs as (

    select * from {{ ref('stg_waste_logs') }}

),

receipt_quality as (

    select
        purchase_orders.supplier_id,
        sum(po_receipts.quantity_received) as total_quantity_received,
        sum(
            case
                when po_receipts.quality_status = 'rejected' then po_receipts.quantity_received
                else 0
            end
        ) as total_quantity_rejected,
        count(po_receipts.receipt_id) as total_receipts,
        sum(
            case
                when po_receipts.quality_status = 'rejected' then 1
                else 0
            end
        ) as rejected_receipts

    from po_receipts

    inner join po_line_items
        on po_receipts.po_line_item_id = po_line_items.po_line_item_id

    inner join purchase_orders
        on po_line_items.purchase_order_id = purchase_orders.purchase_order_id

    group by purchase_orders.supplier_id

),

supplier_waste as (

    select
        purchase_orders.supplier_id,
        sum(waste_logs.quantity_wasted) as total_waste_from_supplier,
        sum(waste_logs.cost_of_waste) as total_waste_cost_from_supplier

    from waste_logs

    inner join po_line_items
        on waste_logs.product_id = po_line_items.product_id

    inner join purchase_orders
        on po_line_items.purchase_order_id = purchase_orders.purchase_order_id

    group by purchase_orders.supplier_id

),

quality_scores as (

    select
        receipt_quality.supplier_id,
        receipt_quality.total_quantity_received,
        receipt_quality.total_quantity_rejected,
        receipt_quality.total_receipts,
        receipt_quality.rejected_receipts,
        case
            when receipt_quality.total_quantity_received > 0
                then receipt_quality.total_quantity_rejected * 1.0
                    / receipt_quality.total_quantity_received
            else 0
        end as defect_rate,
        case
            when receipt_quality.total_quantity_received > 0
                then 1.0 - (receipt_quality.total_quantity_rejected * 1.0
                    / receipt_quality.total_quantity_received)
            else 1.0
        end as quality_score,
        coalesce(supplier_waste.total_waste_from_supplier, 0) as total_waste_quantity,
        coalesce(supplier_waste.total_waste_cost_from_supplier, 0) as total_waste_cost

    from receipt_quality

    left join supplier_waste
        on receipt_quality.supplier_id = supplier_waste.supplier_id

)

select * from quality_scores
