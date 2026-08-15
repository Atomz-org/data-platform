with

purchase_orders as (

    select * from {{ ref('stg_purchase_orders') }}

),

po_line_items as (

    select * from {{ ref('stg_po_line_items') }}

),

po_receipts as (

    select * from {{ ref('stg_po_receipts') }}

),

line_item_fulfillment as (

    select
        po_line_items.po_line_item_id,
        po_line_items.purchase_order_id,
        po_line_items.product_id,
        po_line_items.quantity_ordered,
        coalesce(sum(po_receipts.quantity_received), 0) as total_quantity_received,
        po_line_items.quantity_ordered
            - coalesce(sum(po_receipts.quantity_received), 0) as quantity_outstanding,
        case
            when coalesce(sum(po_receipts.quantity_received), 0) = 0 then 'not_received'
            when coalesce(sum(po_receipts.quantity_received), 0)
                < po_line_items.quantity_ordered then 'partially_received'
            when coalesce(sum(po_receipts.quantity_received), 0)
                >= po_line_items.quantity_ordered then 'fully_received'
        end as line_fulfillment_status

    from po_line_items

    left join po_receipts
        on po_line_items.po_line_item_id = po_receipts.po_line_item_id

    group by
        po_line_items.po_line_item_id,
        po_line_items.purchase_order_id,
        po_line_items.product_id,
        po_line_items.quantity_ordered

),

po_fulfillment as (

    select
        purchase_orders.purchase_order_id,
        purchase_orders.supplier_id,
        purchase_orders.po_status,
        purchase_orders.ordered_at,
        purchase_orders.expected_delivery_at,
        count(line_item_fulfillment.po_line_item_id) as total_line_items,
        sum(line_item_fulfillment.quantity_ordered) as total_quantity_ordered,
        sum(line_item_fulfillment.total_quantity_received) as total_quantity_received,
        sum(
            case
                when line_item_fulfillment.line_fulfillment_status = 'fully_received'
                    then 1
                else 0
            end
        ) as count_lines_fully_received,
        case
            when sum(line_item_fulfillment.total_quantity_received) = 0
                then 'not_fulfilled'
            when sum(
                case
                    when line_item_fulfillment.line_fulfillment_status = 'fully_received'
                        then 1
                    else 0
                end
            ) = count(line_item_fulfillment.po_line_item_id)
                then 'fully_fulfilled'
            else 'partially_fulfilled'
        end as po_fulfillment_status

    from purchase_orders

    left join line_item_fulfillment
        on purchase_orders.purchase_order_id = line_item_fulfillment.purchase_order_id

    group by
        purchase_orders.purchase_order_id,
        purchase_orders.supplier_id,
        purchase_orders.po_status,
        purchase_orders.ordered_at,
        purchase_orders.expected_delivery_at

)

select * from po_fulfillment
