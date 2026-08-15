with

purchase_orders as (

    select * from {{ ref('stg_purchase_orders') }}

),

po_receipts as (

    select * from {{ ref('stg_po_receipts') }}

),

last_receipt_per_po as (

    select
        purchase_order_id,
        min(received_at) as first_received_at,
        max(received_at) as last_received_at

    from po_receipts

    group by purchase_order_id

),

cycle_times as (

    select
        purchase_orders.purchase_order_id,
        purchase_orders.supplier_id,
        purchase_orders.po_status,
        purchase_orders.ordered_at,
        purchase_orders.expected_delivery_at,
        last_receipt_per_po.first_received_at,
        last_receipt_per_po.last_received_at,
        {{ dbt.datediff(
            'purchase_orders.ordered_at',
            'last_receipt_per_po.last_received_at',
            'day'
        ) }} as cycle_time_days,
        {{ dbt.datediff(
            'purchase_orders.ordered_at',
            'purchase_orders.expected_delivery_at',
            'day'
        ) }} as expected_cycle_time_days,
        case
            when last_receipt_per_po.last_received_at is not null
                then {{ dbt.datediff(
                    'purchase_orders.ordered_at',
                    'last_receipt_per_po.last_received_at',
                    'day'
                ) }} - {{ dbt.datediff(
                    'purchase_orders.ordered_at',
                    'purchase_orders.expected_delivery_at',
                    'day'
                ) }}
            else null
        end as cycle_time_variance_days

    from purchase_orders

    left join last_receipt_per_po
        on purchase_orders.purchase_order_id = last_receipt_per_po.purchase_order_id

)

select * from cycle_times
