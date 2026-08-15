with

purchase_orders as (

    select * from {{ ref('stg_purchase_orders') }}

),

po_receipts as (

    select * from {{ ref('stg_po_receipts') }}

),

lead_times as (

    select * from {{ ref('int_lead_time_by_supplier') }}

),

first_receipt_per_po as (

    select
        purchase_order_id,
        min(received_at) as first_received_at

    from po_receipts

    group by purchase_order_id

),

order_lead_times as (

    select
        purchase_orders.supplier_id,
        purchase_orders.purchase_order_id,
        {{ dbt.date_trunc('month', 'purchase_orders.ordered_at') }} as order_month,
        purchase_orders.ordered_at,
        first_receipt_per_po.first_received_at,
        {{ dbt.datediff(
            'purchase_orders.ordered_at',
            'first_receipt_per_po.first_received_at',
            'day'
        ) }} as actual_lead_time_days,
        {{ dbt.datediff(
            'purchase_orders.ordered_at',
            'purchase_orders.expected_delivery_at',
            'day'
        ) }} as expected_lead_time_days

    from purchase_orders

    inner join first_receipt_per_po
        on purchase_orders.purchase_order_id = first_receipt_per_po.purchase_order_id

),

monthly_trends as (

    select
        order_lead_times.supplier_id,
        order_lead_times.order_month,
        count(order_lead_times.purchase_order_id) as order_count,
        avg(order_lead_times.actual_lead_time_days) as avg_lead_time_days,
        min(order_lead_times.actual_lead_time_days) as min_lead_time_days,
        max(order_lead_times.actual_lead_time_days) as max_lead_time_days,
        avg(order_lead_times.actual_lead_time_days
            - order_lead_times.expected_lead_time_days) as avg_variance_days,
        sum(
            case
                when order_lead_times.actual_lead_time_days
                    <= order_lead_times.expected_lead_time_days
                    then 1
                else 0
            end
        ) * 1.0 / nullif(count(order_lead_times.purchase_order_id), 0)
            as monthly_on_time_rate,
        lead_times.avg_lead_time_days as overall_avg_lead_time_days,
        lead_times.on_time_delivery_rate as overall_on_time_rate

    from order_lead_times

    left join lead_times
        on order_lead_times.supplier_id = lead_times.supplier_id

    group by
        order_lead_times.supplier_id,
        order_lead_times.order_month,
        lead_times.avg_lead_time_days,
        lead_times.on_time_delivery_rate

)

select * from monthly_trends
