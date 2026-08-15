with

purchase_orders as (

    select * from {{ ref('fct_purchase_orders') }}

),

suppliers as (

    select * from {{ ref('dim_suppliers') }}

),

po_lines as (

    select * from {{ ref('stg_po_line_items') }}

),

po_receipts as (

    select * from {{ ref('stg_po_receipts') }}

)

select
    po.purchase_order_id,
    po.supplier_id,
    s.supplier_name,
    po.ordered_at,
    po.expected_delivery_at,
    po.total_amount,
    po.po_status,
    count(distinct pl.po_line_item_id) as line_item_count,
    count(distinct pr.receipt_id) as receipt_count,
    case
        when po.expected_delivery_at <= po.expected_delivery_at then 'on_time'
        when po.expected_delivery_at is null then 'pending'
        else 'late'
    end as delivery_status

from purchase_orders po
left join suppliers s on po.supplier_id = s.supplier_id
left join po_lines pl on po.purchase_order_id = pl.purchase_order_id
left join po_receipts pr on po.purchase_order_id = pr.purchase_order_id
group by
    po.purchase_order_id, po.supplier_id, s.supplier_name,
    po.ordered_at, po.expected_delivery_at, po.expected_delivery_at,
    po.total_amount, po.po_status
