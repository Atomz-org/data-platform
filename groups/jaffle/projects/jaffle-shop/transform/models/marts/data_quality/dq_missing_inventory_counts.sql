with

products as (

    select product_id, product_name from {{ ref('stg_products') }}

),

locations as (

    select location_id, location_name from {{ ref('stg_locations') }}

),

-- All product-location combinations that should exist
expected_combinations as (

    select
        p.product_id,
        p.product_name,
        l.location_id,
        l.location_name

    from products as p
    cross join locations as l

),

inventory as (

    select
        product_id,
        location_id,
        last_movement_at
    from {{ ref('int_inventory_current_level') }}

),

missing as (

    select
        ec.product_id,
        ec.product_name,
        ec.location_id,
        ec.location_name,
        inv.last_movement_at,
        case
            when inv.product_id is null then 'never_counted'
            when inv.last_movement_at < {{ dbt.current_timestamp() }} - interval '30 days'
            then 'stale_count'
            else 'recent'
        end as count_status

    from expected_combinations as ec

    left join inventory as inv
        on ec.product_id = inv.product_id
        and ec.location_id = inv.location_id

    where inv.product_id is null
       or inv.last_movement_at < {{ dbt.current_timestamp() }} - interval '30 days'

)

select * from missing
