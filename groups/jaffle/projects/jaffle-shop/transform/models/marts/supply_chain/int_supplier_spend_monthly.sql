with

purchase_orders as (

    select * from {{ ref('stg_purchase_orders') }}

),

po_line_items as (

    select * from {{ ref('stg_po_line_items') }}

),

suppliers as (

    select * from {{ ref('stg_suppliers') }}

),

monthly_spend as (

    select
        purchase_orders.supplier_id,
        suppliers.supplier_name,
        {{ dbt.date_trunc('month', 'purchase_orders.ordered_at') }} as order_month,
        count(distinct purchase_orders.purchase_order_id) as count_purchase_orders,
        sum(po_line_items.line_total) as total_spend,
        sum(po_line_items.quantity_ordered) as total_quantity_ordered,
        avg(po_line_items.unit_cost) as avg_unit_cost

    from purchase_orders

    inner join po_line_items
        on purchase_orders.purchase_order_id = po_line_items.purchase_order_id

    left join suppliers
        on purchase_orders.supplier_id = suppliers.supplier_id

    group by
        purchase_orders.supplier_id,
        suppliers.supplier_name,
        {{ dbt.date_trunc('month', 'purchase_orders.ordered_at') }}

)

select * from monthly_spend
