with

pos as (
    select * from {{ ref('stg_purchase_orders') }}
),

suppliers as (
    select supplier_id, supplier_name from {{ ref('stg_suppliers') }}
),

final as (
    select
        po.purchase_order_id,
        po.supplier_id,
        s.supplier_name,
        po.ordered_at,
        po.expected_delivery_at,
        po.total_amount,
        po.po_status
    from pos as po
    left join suppliers as s on po.supplier_id = s.supplier_id
)

select * from final
