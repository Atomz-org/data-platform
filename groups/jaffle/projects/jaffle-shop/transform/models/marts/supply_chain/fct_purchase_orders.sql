with

purchase_orders_enriched as (

    select * from {{ ref('int_purchase_orders_enriched') }}

),

final as (

    select
        purchase_order_id,
        supplier_id,
        supplier_name,
        warehouse_id,
        po_status,
        total_amount,
        count_line_items,
        total_quantity_ordered,
        calculated_total_amount,
        ordered_at,
        expected_delivery_at,
        created_at,
        case
            when po_status = 'cancelled' then true
            else false
        end as is_cancelled,
        case
            when po_status in ('received', 'closed') then true
            else false
        end as is_completed

    from purchase_orders_enriched

)

select * from final
