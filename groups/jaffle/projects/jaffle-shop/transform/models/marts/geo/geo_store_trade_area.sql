with

stores as (

    select * from {{ ref('dim_store_profile') }}

),

store_pairs as (

    select
        a.location_id,
        a.store_name,
        a.location_id as store_location_id,
        b.location_id as nearby_store_id,
        b.store_name as nearby_store_name,
        b.location_id as nearby_location_id,
        row_number() over (
            partition by a.location_id
            order by b.location_id
        ) as distance_rank

    from stores a
    cross join stores b
    where a.location_id != b.location_id

),

nearest as (

    select * from store_pairs where distance_rank = 1

)

select
    s.location_id,
    s.store_name,
    s.location_id as store_location_id,
    n.nearby_store_id as nearest_store_id,
    n.nearby_store_name as nearest_store_name,
    n.distance_rank as nearest_store_distance_proxy,
    case
        when n.distance_rank <= 2 then 'high_overlap_risk'
        when n.distance_rank <= 5 then 'moderate_overlap_risk'
        else 'low_overlap_risk'
    end as trade_area_overlap_risk

from stores s
left join nearest n on s.location_id = n.location_id
