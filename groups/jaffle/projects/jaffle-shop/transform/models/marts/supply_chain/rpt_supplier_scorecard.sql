with

lead_times as (

    select * from {{ ref('int_lead_time_by_supplier') }}

),

fulfillment as (

    select * from {{ ref('int_po_fulfillment_status') }}

),

spend as (

    select * from {{ ref('int_supplier_spend_monthly') }}

),

fulfillment_by_supplier as (

    select
        supplier_id,
        count(purchase_order_id) as total_purchase_orders,
        sum(
            case when po_fulfillment_status = 'fully_fulfilled' then 1 else 0 end
        ) as fully_fulfilled_orders,
        sum(
            case when po_fulfillment_status = 'partially_fulfilled' then 1 else 0 end
        ) as partially_fulfilled_orders,
        sum(
            case when po_fulfillment_status = 'not_fulfilled' then 1 else 0 end
        ) as not_fulfilled_orders,
        sum(
            case when po_fulfillment_status = 'fully_fulfilled' then 1 else 0 end
        ) * 1.0 / nullif(count(purchase_order_id), 0) as fulfillment_rate

    from fulfillment

    group by supplier_id

),

total_spend_by_supplier as (

    select
        supplier_id,
        supplier_name,
        sum(total_spend) as lifetime_spend,
        avg(total_spend) as avg_monthly_spend,
        count(distinct order_month) as active_months

    from spend

    group by supplier_id, supplier_name

),

scorecard as (

    select
        total_spend_by_supplier.supplier_id,
        total_spend_by_supplier.supplier_name,
        total_spend_by_supplier.lifetime_spend,
        total_spend_by_supplier.avg_monthly_spend,
        total_spend_by_supplier.active_months,
        fulfillment_by_supplier.total_purchase_orders,
        fulfillment_by_supplier.fulfillment_rate,
        fulfillment_by_supplier.fully_fulfilled_orders,
        fulfillment_by_supplier.partially_fulfilled_orders,
        lead_times.avg_lead_time_days,
        lead_times.avg_lead_time_variance_days,
        lead_times.on_time_delivery_rate,
        lead_times.count_completed_orders

    -- NOTE: join all suppliers to get complete scorecard view
    from total_spend_by_supplier

    inner join fulfillment_by_supplier
        on total_spend_by_supplier.supplier_id = fulfillment_by_supplier.supplier_id

    left join lead_times
        on total_spend_by_supplier.supplier_id = lead_times.supplier_id

)

select * from scorecard
