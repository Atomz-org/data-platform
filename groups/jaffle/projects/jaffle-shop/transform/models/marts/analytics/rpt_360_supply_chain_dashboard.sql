with

supplier_reliability as (

    select * from {{ ref('scr_supplier_reliability') }}

),

inventory_levels as (

    select
        product_id,
        location_id,
        current_quantity,
        total_movements
    from {{ ref('int_inventory_current_level') }}

),

waste_summary as (

    select
        location_id,
        sum(quantity_wasted) as total_waste_quantity,
        sum(cost_of_waste) as total_waste_cost,
        count(waste_log_id) as waste_events
    from {{ ref('stg_waste_logs') }}
    group by 1

),

inventory_summary as (

    select
        count(distinct product_id) as products_in_stock,
        count(distinct location_id) as stocked_locations,
        sum(current_quantity) as total_units_in_stock,
        0 as total_inventory_value
    from inventory_levels

),

supplier_summary as (

    select
        count(distinct supplier_id) as total_suppliers,
        avg(reliability_score) as avg_reliability_score,
        count(case when reliability_tier = 'high' then 1 end) as high_reliability_suppliers,
        count(case when reliability_tier = 'low' then 1 end) as low_reliability_suppliers
    from supplier_reliability

),

final as (

    select
        ss.total_suppliers,
        ss.avg_reliability_score,
        ss.high_reliability_suppliers,
        ss.low_reliability_suppliers,
        inv.products_in_stock,
        inv.stocked_locations,
        inv.total_units_in_stock,
        inv.total_inventory_value
    from supplier_summary as ss
    cross join inventory_summary as inv

)

select * from final
