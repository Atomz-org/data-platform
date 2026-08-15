with

inventory as (

    select
        product_id,
        location_id,
        current_quantity
    from {{ ref('int_inventory_current_level') }}

),

prices as (

    select
        ingredient_id as product_id,
        avg(unit_cost) as avg_unit_cost
    from {{ ref('stg_ingredient_prices') }}
    group by 1

),

store_names as (

    select location_id, location_name
    from {{ ref('stg_locations') }}

),

final as (

    select
        inv.product_id,
        inv.location_id,
        s.location_name,
        inv.current_quantity,
        coalesce(p.avg_unit_cost, 0) as unit_value,
        inv.current_quantity * coalesce(p.avg_unit_cost, 0) as inventory_value,
        -- Monthly holding cost at 20% annual rate / 12
        inv.current_quantity * coalesce(p.avg_unit_cost, 0) * 0.20 / 12 as monthly_carrying_cost,
        inv.current_quantity * coalesce(p.avg_unit_cost, 0) * 0.20 as annual_carrying_cost
    from inventory as inv
    left join prices as p on inv.product_id = p.product_id
    inner join store_names as s on inv.location_id = s.location_id

)

select * from final
