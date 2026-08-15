with

pli as (
    select * from {{ ref('stg_po_line_items') }}
),

po as (
    select * from {{ ref('stg_purchase_orders') }}
),

line_items as (

    select
        pli.product_id,
        pli.unit_cost,
        pli.quantity_ordered,
        po.supplier_id,
        po.ordered_at
    from pli
    inner join po
        on pli.purchase_order_id = po.purchase_order_id

),

supplier_names as (

    select supplier_id, supplier_name
    from {{ ref('stg_suppliers') }}

),

supplier_product_avg as (

    select
        li.product_id,
        li.supplier_id,
        sn.supplier_name,
        count(*) as purchase_count,
        avg(li.unit_cost) as avg_unit_cost,
        min(li.unit_cost) as min_unit_cost,
        max(li.unit_cost) as max_unit_cost,
        sum(li.quantity_ordered) as total_quantity
    from line_items as li
    inner join supplier_names as sn on li.supplier_id = sn.supplier_id
    group by 1, 2, 3

),

product_best as (

    select
        product_id,
        min(avg_unit_cost) as lowest_avg_cost
    from supplier_product_avg
    group by 1

),

final as (

    select
        spa.product_id,
        spa.supplier_id,
        spa.supplier_name,
        spa.purchase_count,
        spa.avg_unit_cost,
        spa.min_unit_cost,
        spa.max_unit_cost,
        spa.total_quantity,
        pb.lowest_avg_cost,
        spa.avg_unit_cost - pb.lowest_avg_cost as cost_premium,
        case
            when pb.lowest_avg_cost > 0
            then (spa.avg_unit_cost - pb.lowest_avg_cost) / pb.lowest_avg_cost * 100
            else 0
        end as cost_premium_pct,
        case
            when spa.avg_unit_cost = pb.lowest_avg_cost then 'lowest_cost'
            when (spa.avg_unit_cost - pb.lowest_avg_cost) / nullif(pb.lowest_avg_cost, 0) <= 0.05 then 'competitive'
            else 'premium'
        end as price_position
    from supplier_product_avg as spa
    inner join product_best as pb on spa.product_id = pb.product_id

)

select * from final
