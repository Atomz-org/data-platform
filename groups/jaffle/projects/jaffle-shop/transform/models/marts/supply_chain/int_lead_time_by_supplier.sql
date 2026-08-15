with

purchase_orders as (

    select * from {{ ref('stg_purchase_orders') }}

),

po_receipts as (

    select * from {{ ref('stg_po_receipts') }}

),

first_receipt_per_po as (

    select
        purchase_order_id,
        min(received_at) as first_received_at

    from po_receipts

    group by purchase_order_id

),

lead_times as (

    select
        purchase_orders.supplier_id,
        purchase_orders.purchase_order_id,
        purchase_orders.ordered_at,
        first_receipt_per_po.first_received_at,
        {{ dbt.datediff('purchase_orders.ordered_at', 'first_receipt_per_po.first_received_at', 'day') }}
            as actual_lead_time_days,
        {{ dbt.datediff('purchase_orders.ordered_at', 'purchase_orders.expected_delivery_at', 'day') }}
            as expected_lead_time_days

    from purchase_orders

    inner join first_receipt_per_po
        on purchase_orders.purchase_order_id = first_receipt_per_po.purchase_order_id

),

supplier_lead_time_stats as (

    select
        supplier_id,
        count(purchase_order_id) as count_completed_orders,
        avg(actual_lead_time_days) as avg_lead_time_days,
        min(actual_lead_time_days) as min_lead_time_days,
        max(actual_lead_time_days) as max_lead_time_days,
        avg(expected_lead_time_days) as avg_expected_lead_time_days,
        avg(actual_lead_time_days - expected_lead_time_days) as avg_lead_time_variance_days,
        sum(
            case
                when actual_lead_time_days <= expected_lead_time_days then 1
                else 0
            end
        ) as count_on_time_deliveries

    from lead_times

    group by supplier_id

)

select
    *,
    count_on_time_deliveries * 1.0 / nullif(count_completed_orders, 0) as on_time_delivery_rate

from supplier_lead_time_stats
