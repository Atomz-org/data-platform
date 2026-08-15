with

source as (

    select * from {{ source('marketing', 'raw_loyalty_members') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as loyalty_member_id,
        cast(customer_id as varchar) as customer_id,
        cast(tier_id as varchar) as current_tier_id,

        ---------- text
        status as membership_status,

        ---------- numerics
        lifetime_points,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'enrolled_at') }} as enrolled_at,
        {{ dbt.date_trunc('day', 'last_activity_at') }} as last_activity_at

    from source

)

select * from renamed
