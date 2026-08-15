with

waste_logs as (

    select * from {{ ref('stg_waste_logs') }}

),

current_levels as (

    select * from {{ ref('int_inventory_current_level') }}

),

waste_by_product as (

    select
        product_id,
        count(waste_log_id) as total_waste_events,
        sum(quantity_wasted) as total_quantity_wasted,
        sum(cost_of_waste) as total_cost_of_waste,
        avg(quantity_wasted) as avg_quantity_per_event,
        min(wasted_at) as first_waste_at,
        max(wasted_at) as last_waste_at

    from waste_logs

    group by product_id

),

waste_with_inventory as (

    select
        waste_by_product.product_id,
        waste_by_product.total_waste_events,
        waste_by_product.total_quantity_wasted,
        waste_by_product.total_cost_of_waste,
        waste_by_product.avg_quantity_per_event,
        waste_by_product.first_waste_at,
        waste_by_product.last_waste_at,
        coalesce(inventory_totals.total_inbound, 0) as total_inbound_quantity,
        case
            when coalesce(inventory_totals.total_inbound, 0) > 0
                then waste_by_product.total_quantity_wasted * 1.0
                    / inventory_totals.total_inbound
            else 0
        end as waste_rate

    from waste_by_product

    left join (
        select
            product_id,
            sum(total_inbound) as total_inbound

        from current_levels

        group by product_id
    ) as inventory_totals
        on waste_by_product.product_id = inventory_totals.product_id

)

select * from waste_with_inventory
