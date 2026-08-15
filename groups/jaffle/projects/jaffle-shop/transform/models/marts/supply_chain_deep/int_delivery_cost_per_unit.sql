with

shipments as (

    select * from {{ ref('stg_delivery_shipments') }}

),

receipts as (

    select
        purchase_order_id,
        sum(quantity_received) as total_units_received
    from {{ ref('stg_po_receipts') }}
    group by 1

),

purchase_orders as (

    select
        purchase_order_id,
        total_amount as po_total_cost
    from {{ ref('stg_purchase_orders') }}

),

final as (

    select
        s.shipment_id,
        s.purchase_order_id,
        s.supplier_id,
        s.carrier,
        s.shipped_at,
        s.actual_arrival_at,
        coalesce(r.total_units_received, 0) as units_delivered,
        po.po_total_cost,
        case
            when coalesce(r.total_units_received, 0) > 0
                then round(cast(po.po_total_cost / r.total_units_received as {{ dbt.type_float() }}), 2)
            else null
        end as cost_per_unit_delivered,
        case
            when s.actual_arrival_at is not null
                then {{ dbt.datediff('s.shipped_at', 's.actual_arrival_at', 'day') }}
            else null
        end as transit_days
    from shipments as s
    left join receipts as r
        on s.purchase_order_id = r.purchase_order_id
    left join purchase_orders as po
        on s.purchase_order_id = po.purchase_order_id

)

select * from final
