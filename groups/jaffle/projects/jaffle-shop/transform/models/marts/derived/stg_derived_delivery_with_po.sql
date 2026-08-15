with

deliveries as (
    select * from {{ ref('stg_delivery_shipments') }}
),

pos as (
    select purchase_order_id, supplier_id, ordered_at, total_amount from {{ ref('stg_purchase_orders') }}
),

final as (
    select
        d.shipment_id,
        d.purchase_order_id,
        po.supplier_id,
        po.ordered_at as po_ordered_at,
        po.total_amount as po_total,
        d.shipped_at,
        d.actual_arrival_at,
        d.actual_arrival_at - po.ordered_at as total_lead_time_days,
        d.shipment_status
    from deliveries as d
    left join pos as po on d.purchase_order_id = po.purchase_order_id
)

select * from final
