with

waste_logs as (

    select * from {{ ref('stg_waste_logs') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

final as (

    select
        waste_logs.waste_log_id,
        waste_logs.product_id,
        products.product_name,
        products.product_type,
        waste_logs.location_id,
        locations.location_name,
        waste_logs.waste_reason,
        waste_logs.quantity_wasted,
        waste_logs.cost_of_waste,
        waste_logs.wasted_at

    from waste_logs

    left join products
        on waste_logs.product_id = products.product_id

    left join locations
        on waste_logs.location_id = locations.location_id

)

select * from final
