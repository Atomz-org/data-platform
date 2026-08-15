with

po_line_items as (
    select * from {{ ref('stg_po_line_items') }}
),

depletion_rates as (

    select * from {{ ref('int_stock_depletion_rate') }}

),

lead_times as (

    select * from {{ ref('int_lead_time_by_supplier') }}

),

purchase_orders as (

    select * from {{ ref('stg_purchase_orders') }}

),

product_supplier_map as (

    select distinct
        po_line_items.product_id,
        purchase_orders.supplier_id

    from po_line_items

    inner join purchase_orders
        on po_line_items.purchase_order_id = purchase_orders.purchase_order_id

),

reorder_points as (

    select
        depletion_rates.product_id,
        depletion_rates.location_id,
        depletion_rates.current_quantity,
        depletion_rates.daily_depletion_rate,
        depletion_rates.estimated_days_of_stock,
        coalesce(lead_times.avg_lead_time_days, 7) as supplier_avg_lead_time_days,
        -- Reorder point = daily usage * lead time + safety stock (7 days buffer)
        depletion_rates.daily_depletion_rate
            * (coalesce(lead_times.avg_lead_time_days, 7) + 7)
            as reorder_point,
        -- Reorder quantity = 30 days of stock
        depletion_rates.daily_depletion_rate * 30 as suggested_reorder_quantity,
        case
            when depletion_rates.current_quantity
                <= depletion_rates.daily_depletion_rate
                    * (coalesce(lead_times.avg_lead_time_days, 7) + 7)
                then true
            else false
        end as needs_reorder

    from depletion_rates

    left join product_supplier_map
        on depletion_rates.product_id = product_supplier_map.product_id

    left join lead_times
        on product_supplier_map.supplier_id = lead_times.supplier_id

)

select * from reorder_points
