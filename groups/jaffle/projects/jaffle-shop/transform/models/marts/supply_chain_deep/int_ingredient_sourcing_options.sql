with

po_items as (

    select * from {{ ref('stg_po_line_items') }}

),

purchase_orders as (

    select
        purchase_order_id,
        supplier_id,
        ordered_at
    from {{ ref('stg_purchase_orders') }}

),

suppliers as (

    select
        supplier_id,
        supplier_name,
        is_active
    from {{ ref('stg_suppliers') }}

),

supplier_product_pricing as (

    select
        po.supplier_id,
        s.supplier_name,
        s.is_active as supplier_is_active,
        pi.product_id,
        count(distinct po.purchase_order_id) as order_count,
        avg(pi.unit_cost) as avg_unit_cost,
        min(pi.unit_cost) as min_unit_cost,
        max(pi.unit_cost) as max_unit_cost,
        sum(pi.quantity_ordered) as total_quantity_ordered,
        max(po.ordered_at) as last_order_date
    from po_items as pi
    inner join purchase_orders as po
        on pi.purchase_order_id = po.purchase_order_id
    left join suppliers as s
        on po.supplier_id = s.supplier_id
    group by 1, 2, 3, 4

),

ranked as (

    select
        *,
        rank() over (
            partition by product_id
            order by avg_unit_cost asc
        ) as cost_rank,
        count(*) over (partition by product_id) as available_supplier_count
    from supplier_product_pricing

)

select * from ranked
