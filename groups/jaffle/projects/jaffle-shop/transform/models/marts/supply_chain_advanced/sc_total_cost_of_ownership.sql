with

pli as (
    select * from {{ ref('stg_po_line_items') }}
),

po as (
    select * from {{ ref('stg_purchase_orders') }}
),

d as (
    select * from {{ ref('fct_deliveries') }}
),

w as (
    select * from {{ ref('fct_waste_events') }}
),

purchase_cost as (

    select
        po.supplier_id,
        sum(pli.line_total) as total_material_cost,
        count(distinct po.purchase_order_id) as total_pos,
        -- Admin cost: $50 per PO
        count(distinct po.purchase_order_id) * 50.0 as admin_cost
    from pli
    inner join po
        on pli.purchase_order_id = po.purchase_order_id
    group by 1

),

delivery_cost as (

    select
        po.supplier_id,
        sum(d.po_total_amount) as total_delivery_cost
    from d
    inner join po
        on d.purchase_order_id = po.purchase_order_id
    group by 1

),

quality_cost as (

    -- Proxy: waste events for supplier products
    select
        po.supplier_id,
        sum(w.cost_of_waste) as quality_loss_cost
    from w
    inner join pli
        on w.product_id = pli.product_id
    inner join po
        on pli.purchase_order_id = po.purchase_order_id
    group by 1

),

supplier_names as (

    select supplier_id, supplier_name
    from {{ ref('dim_suppliers') }}

),

final as (

    select
        sn.supplier_id,
        sn.supplier_name,
        pc.total_material_cost,
        coalesce(dc.total_delivery_cost, 0) as total_delivery_cost,
        coalesce(qc.quality_loss_cost, 0) as quality_loss_cost,
        pc.admin_cost,
        pc.total_material_cost
            + coalesce(dc.total_delivery_cost, 0)
            + coalesce(qc.quality_loss_cost, 0)
            + pc.admin_cost as total_cost_of_ownership,
        case
            when pc.total_material_cost > 0
            then (pc.total_material_cost
                + coalesce(dc.total_delivery_cost, 0)
                + coalesce(qc.quality_loss_cost, 0)
                + pc.admin_cost)
                / pc.total_material_cost
            else null
        end as tco_multiplier
    from purchase_cost as pc
    inner join supplier_names as sn on pc.supplier_id = sn.supplier_id
    left join delivery_cost as dc on pc.supplier_id = dc.supplier_id
    left join quality_cost as qc on pc.supplier_id = qc.supplier_id

)

select * from final
