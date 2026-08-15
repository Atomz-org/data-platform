with

fulfillment as (

    select * from {{ ref('int_po_fulfillment_status') }}

),

suppliers as (

    select * from {{ ref('stg_suppliers') }}

),

summary as (

    select
        fulfillment.supplier_id,
        suppliers.supplier_name,
        fulfillment.purchase_order_id,
        fulfillment.po_status,
        fulfillment.po_fulfillment_status,
        fulfillment.ordered_at,
        fulfillment.expected_delivery_at,
        fulfillment.total_line_items,
        fulfillment.total_quantity_ordered,
        fulfillment.total_quantity_received,
        fulfillment.count_lines_fully_received,
        case
            when fulfillment.total_quantity_ordered > 0
                then fulfillment.total_quantity_received * 1.0
                    / fulfillment.total_quantity_ordered
            else 0
        end as quantity_fill_rate,
        case
            when fulfillment.total_line_items > 0
                then fulfillment.count_lines_fully_received * 1.0
                    / fulfillment.total_line_items
            else 0
        end as line_fill_rate

    from fulfillment

    left join suppliers
        on fulfillment.supplier_id = suppliers.supplier_id

)

select * from summary
