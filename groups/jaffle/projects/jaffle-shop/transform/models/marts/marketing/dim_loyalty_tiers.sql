with

loyalty_tiers as (

    select * from {{ ref('stg_loyalty_tiers') }}

),

final as (

    select
        tier_id,
        tier_name,
        tier_description,
        minimum_points,
        maximum_points,
        points_multiplier,
        annual_reward,

        -- Derived fields
        case
            when maximum_points is not null
            then maximum_points - minimum_points + 1
            else null
        end as tier_points_range,
        row_number() over (order by minimum_points asc) as tier_rank

    from loyalty_tiers

)

select * from final
