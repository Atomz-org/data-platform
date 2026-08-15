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
        po.supplier_id
    from pli
    inner join po
        on pli.purchase_order_id = po.purchase_order_id

),

supplier_info as (

    select supplier_id, supplier_name, is_active
    from {{ ref('stg_suppliers') }}

),

product_suppliers as (

    select
        li.product_id,
        count(distinct li.supplier_id) as total_suppliers,
        count(distinct case when si.is_active then li.supplier_id end) as active_suppliers,
        count(*) as total_line_items
    from line_items as li
    inner join supplier_info as si on li.supplier_id = si.supplier_id
    group by 1

),

final as (

    select
        product_id,
        total_suppliers,
        active_suppliers,
        total_line_items,
        case
            when active_suppliers = 0 then 'no_active_supplier'
            when active_suppliers = 1 then 'single_source'
            when active_suppliers = 2 then 'dual_source'
            else 'multi_source'
        end as diversification_status,
        case
            when active_suppliers <= 1 then 'high'
            when active_suppliers = 2 then 'medium'
            else 'low'
        end as supply_risk_level
    from product_suppliers

)

select * from final
