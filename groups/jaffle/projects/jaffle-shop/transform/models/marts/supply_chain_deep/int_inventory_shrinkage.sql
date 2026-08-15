with

counted_inventory as (

    select
        product_id,
        location_id,
        quantity_on_hand as counted_quantity,
        counted_at
    from {{ ref('stg_inventory_counts') }}

),

latest_count as (

    select
        product_id,
        location_id,
        counted_quantity,
        counted_at,
        row_number() over (
            partition by product_id, location_id
            order by counted_at desc
        ) as count_recency
    from counted_inventory

),

expected_inventory as (

    select
        product_id,
        location_id,
        current_quantity as expected_quantity
    from {{ ref('int_inventory_current_level') }}

),

final as (

    select
        lc.product_id,
        lc.location_id,
        lc.counted_quantity,
        coalesce(ei.expected_quantity, 0) as expected_quantity,
        lc.counted_at as last_count_date,
        coalesce(ei.expected_quantity, 0) - lc.counted_quantity as shrinkage_quantity,
        case
            when coalesce(ei.expected_quantity, 0) > 0
                then round(cast(
                    (coalesce(ei.expected_quantity, 0) - lc.counted_quantity) * 100.0
                    / ei.expected_quantity
                as {{ dbt.type_float() }}), 2)
            else 0
        end as shrinkage_pct,
        case
            when coalesce(ei.expected_quantity, 0) - lc.counted_quantity > 0
                then 'shortage'
            when coalesce(ei.expected_quantity, 0) - lc.counted_quantity < 0
                then 'surplus'
            else 'match'
        end as shrinkage_status
    from latest_count as lc
    left join expected_inventory as ei
        on lc.product_id = ei.product_id
        and lc.location_id = ei.location_id
    where lc.count_recency = 1

)

select * from final
