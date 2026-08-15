with

pli as (
    select * from {{ ref('stg_po_line_items') }}
),

por as (
    select * from {{ ref('stg_po_receipts') }}
),

ordered as (

    select
        pli.purchase_order_id,
        pli.product_id,
        pli.quantity_ordered,
        pli.unit_cost as ordered_unit_cost
    from pli

),

received as (

    select
        por.purchase_order_id,
        pli.product_id,
        por.quantity_received,
        por.received_at
    from por
    inner join pli
        on por.po_line_item_id = pli.po_line_item_id

),

matched as (

    select
        o.purchase_order_id,
        o.product_id,
        o.quantity_ordered,
        coalesce(r.quantity_received, 0) as quantity_received,
        o.quantity_ordered - coalesce(r.quantity_received, 0) as quantity_variance,
        case
            when o.quantity_ordered > 0
            then abs(o.quantity_ordered - coalesce(r.quantity_received, 0))
                / cast(o.quantity_ordered as {{ dbt.type_float() }}) * 100
            else 0
        end as variance_pct,
        case
            when coalesce(r.quantity_received, 0) = o.quantity_ordered then 'exact_match'
            when coalesce(r.quantity_received, 0) > o.quantity_ordered then 'over_delivered'
            when coalesce(r.quantity_received, 0) = 0 then 'not_received'
            else 'under_delivered'
        end as accuracy_status
    from ordered as o
    left join received as r
        on o.purchase_order_id = r.purchase_order_id
        and o.product_id = r.product_id

),

summary as (

    select
        accuracy_status,
        count(*) as line_item_count,
        avg(variance_pct) as avg_variance_pct,
        sum(abs(quantity_variance)) as total_variance_units
    from matched
    group by 1

)

select * from summary
