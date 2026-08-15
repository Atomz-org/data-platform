with

source as (

    select * from {{ source('marketing', 'raw_loyalty_tiers') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as tier_id,

        ---------- text
        name as tier_name,
        description as tier_description,

        ---------- numerics
        min_points as minimum_points,
        max_points as maximum_points,
        points_multiplier,
        {{ cents_to_dollars('annual_reward') }} as annual_reward

    from source

)

select * from renamed
