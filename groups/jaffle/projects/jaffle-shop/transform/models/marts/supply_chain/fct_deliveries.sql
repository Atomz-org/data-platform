with

delivery_tracking as (

    select * from {{ ref('int_delivery_tracking') }}

),

final as (

    select
        shipment_id,
        purchase_order_id,
        supplier_id,
        destination_id,
        destination_type,
        carrier,
        tracking_number,
        shipment_status,
        po_status,
        po_total_amount,
        destination_warehouse_name,
        destination_city,
        shipped_at,
        estimated_arrival_at,
        actual_arrival_at,
        actual_transit_days,
        expected_transit_days,
        is_on_time,
        case
            when shipment_status = 'delivered' then true
            else false
        end as is_delivered,
        case
            when shipment_status = 'delayed' then true
            else false
        end as is_delayed

    from delivery_tracking

)

select * from final
