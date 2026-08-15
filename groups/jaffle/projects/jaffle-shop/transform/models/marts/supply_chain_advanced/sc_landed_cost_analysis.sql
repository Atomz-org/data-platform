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

purchase_costs as (

    select
        pli.product_id,
        po.supplier_id,
        sum(pli.line_total) as total_purchase_cost,
        sum(pli.quantity_ordered) as total_quantity_purchased
    from pli
    inner join po
        on pli.purchase_order_id = po.purchase_order_id
    group by 1, 2

),

delivery_costs as (

    select
        po.supplier_id,
        sum(d.po_total_amount) as total_delivery_cost,
        count(*) as delivery_count
    from d
    inner join po
        on d.purchase_order_id = po.purchase_order_id
    group by 1

),

cost_of_wastes as (

    select
        product_id,
        sum(cost_of_waste) as total_cost_of_waste
    from {{ ref('fct_waste_events') }}
    group by 1

),

final as (

    select
        pc.product_id,
        pc.supplier_id,
        pc.total_purchase_cost,
        pc.total_quantity_purchased,
        coalesce(dc.total_delivery_cost, 0) as allocated_delivery_cost,
        coalesce(wc.total_cost_of_waste, 0) as product_cost_of_waste,
        pc.total_purchase_cost
            + coalesce(dc.total_delivery_cost, 0)
            + coalesce(wc.total_cost_of_waste, 0) as total_landed_cost,
        case
            when pc.total_quantity_purchased > 0
            then (pc.total_purchase_cost
                + coalesce(dc.total_delivery_cost, 0)
                + coalesce(wc.total_cost_of_waste, 0))
                / pc.total_quantity_purchased
            else null
        end as landed_cost_per_unit,
        case
            when pc.total_purchase_cost > 0
            then pc.total_purchase_cost / pc.total_quantity_purchased
            else null
        end as raw_cost_per_unit
    from purchase_costs as pc
    left join delivery_costs as dc on pc.supplier_id = dc.supplier_id
    left join cost_of_wastes as wc on pc.product_id = wc.product_id

)

select * from final
