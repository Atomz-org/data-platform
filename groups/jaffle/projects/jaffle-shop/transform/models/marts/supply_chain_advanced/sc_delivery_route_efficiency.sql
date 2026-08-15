with

deliveries as (

    select
        shipment_id,
        purchase_order_id,
        shipped_at,
        actual_arrival_at,
        shipment_status,
        po_total_amount,
        {{ dbt.datediff('shipped_at', 'actual_arrival_at', 'day') }} as transit_days
    from {{ ref('fct_deliveries') }}

),

po_info as (

    select
        purchase_order_id,
        supplier_id,
        total_amount
    from {{ ref('fct_purchase_orders') }}

),

supplier_names as (

    select supplier_id, supplier_name
    from {{ ref('dim_suppliers') }}

),

final as (

    select
        sn.supplier_id,
        sn.supplier_name,
        count(*) as total_deliveries,
        avg(d.po_total_amount) as avg_po_total_amount,
        sum(d.po_total_amount) as total_po_total_amount,
        avg(d.transit_days) as avg_transit_days,
        sum(po.total_amount) as total_goods_value,
        case
            when sum(po.total_amount) > 0
            then sum(d.po_total_amount) / sum(po.total_amount) * 100
            else 0
        end as po_total_amount_pct_of_goods,
        case
            when count(*) > 0
            then sum(d.po_total_amount) / count(*)
            else 0
        end as cost_per_delivery
    from deliveries as d
    inner join po_info as po on d.purchase_order_id = po.purchase_order_id
    inner join supplier_names as sn on po.supplier_id = sn.supplier_id
    group by 1, 2

)

select * from final
