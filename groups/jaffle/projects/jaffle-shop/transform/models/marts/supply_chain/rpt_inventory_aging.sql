with

inventory_movements as (

    select * from {{ ref('fct_inventory_movements') }}

),

last_inbound_per_product_location as (

    select
        product_id,
        product_name,
        location_id,
        location_name,
        max(moved_at) as last_inbound_at

    from inventory_movements

    where is_inbound = true

    group by product_id, product_name, location_id, location_name

),

current_levels as (

    select * from {{ ref('int_inventory_current_level') }}

),

aging as (

    select
        last_inbound.product_id,
        last_inbound.product_name,
        last_inbound.location_id,
        last_inbound.location_name,
        current_levels.current_quantity,
        last_inbound.last_inbound_at,
        {{ dbt.datediff(
            'last_inbound.last_inbound_at',
            dbt.current_timestamp(),
            'day'
        ) }} as days_since_last_inbound,
        case
            when {{ dbt.datediff(
                'last_inbound.last_inbound_at',
                dbt.current_timestamp(),
                'day'
            ) }} > 90 then '90+ days'
            when {{ dbt.datediff(
                'last_inbound.last_inbound_at',
                dbt.current_timestamp(),
                'day'
            ) }} > 60 then '61-90 days'
            when {{ dbt.datediff(
                'last_inbound.last_inbound_at',
                dbt.current_timestamp(),
                'day'
            ) }} > 30 then '31-60 days'
            else '0-30 days'
        end as aging_bucket,
        case
            when {{ dbt.datediff(
                'last_inbound.last_inbound_at',
                dbt.current_timestamp(),
                'day'
            ) }} > 90 then 'critical'
            when {{ dbt.datediff(
                'last_inbound.last_inbound_at',
                dbt.current_timestamp(),
                'day'
            ) }} > 60 then 'warning'
            when {{ dbt.datediff(
                'last_inbound.last_inbound_at',
                dbt.current_timestamp(),
                'day'
            ) }} > 30 then 'monitor'
            else 'fresh'
        end as aging_status

    from last_inbound_per_product_location as last_inbound

    inner join current_levels
        on last_inbound.product_id = current_levels.product_id
        and last_inbound.location_id = current_levels.location_id

    where current_levels.current_quantity > 0

)

select * from aging
