with

delivery_shipments as (

    select * from {{ ref('stg_delivery_shipments') }}

),

purchase_orders as (

    select * from {{ ref('stg_purchase_orders') }}

),

warehouses as (

    select * from {{ ref('stg_warehouses') }}

),

tracking as (

    select
        delivery_shipments.shipment_id,
        delivery_shipments.purchase_order_id,
        delivery_shipments.supplier_id,
        delivery_shipments.destination_id,
        delivery_shipments.destination_type,
        delivery_shipments.carrier,
        delivery_shipments.tracking_number,
        delivery_shipments.shipment_status,
        delivery_shipments.shipped_at,
        delivery_shipments.estimated_arrival_at,
        delivery_shipments.actual_arrival_at,
        purchase_orders.po_status,
        purchase_orders.total_amount as po_total_amount,
        warehouses.warehouse_name as destination_warehouse_name,
        warehouses.city as destination_city,
        case
            when delivery_shipments.actual_arrival_at is not null
                then {{ dbt.datediff(
                    'delivery_shipments.shipped_at',
                    'delivery_shipments.actual_arrival_at',
                    'day'
                ) }}
            else null
        end as actual_transit_days,
        case
            when delivery_shipments.estimated_arrival_at is not null
                then {{ dbt.datediff(
                    'delivery_shipments.shipped_at',
                    'delivery_shipments.estimated_arrival_at',
                    'day'
                ) }}
            else null
        end as expected_transit_days,
        case
            when delivery_shipments.actual_arrival_at is not null
                and delivery_shipments.actual_arrival_at
                    <= delivery_shipments.estimated_arrival_at
                then true
            when delivery_shipments.actual_arrival_at is not null
                and delivery_shipments.actual_arrival_at
                    > delivery_shipments.estimated_arrival_at
                then false
            else null
        end as is_on_time

    from delivery_shipments

    left join purchase_orders
        on delivery_shipments.purchase_order_id = purchase_orders.purchase_order_id

    left join warehouses
        on delivery_shipments.destination_id = warehouses.warehouse_id
        and delivery_shipments.destination_type = 'warehouse'

)

select * from tracking
