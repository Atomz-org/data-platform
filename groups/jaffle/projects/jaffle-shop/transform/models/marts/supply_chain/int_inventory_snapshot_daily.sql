with

inventory_counts as (

    select * from {{ ref('stg_inventory_counts') }}

),

current_levels as (

    select * from {{ ref('int_inventory_current_level') }}

),

latest_counts as (

    select
        product_id,
        location_id,
        quantity_on_hand as counted_on_hand,
        quantity_reserved as counted_reserved,
        quantity_available as counted_available,
        counted_at,
        row_number() over (
            partition by product_id, location_id
            order by counted_at desc
        ) as count_recency_rank

    from inventory_counts

),

snapshot as (

    select
        coalesce(latest_counts.product_id, current_levels.product_id) as product_id,
        coalesce(latest_counts.location_id, current_levels.location_id) as location_id,
        latest_counts.counted_on_hand,
        latest_counts.counted_reserved,
        latest_counts.counted_available,
        latest_counts.counted_at as last_count_date,
        current_levels.current_quantity as system_quantity,
        current_levels.last_movement_at,
        current_levels.current_quantity
            - coalesce(latest_counts.counted_on_hand, 0) as count_variance

    from latest_counts

    full outer join current_levels
        on latest_counts.product_id = current_levels.product_id
        and latest_counts.location_id = current_levels.location_id

    where latest_counts.count_recency_rank = 1
        or latest_counts.count_recency_rank is null

)

select * from snapshot
