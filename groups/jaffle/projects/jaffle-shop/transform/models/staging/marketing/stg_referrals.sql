with

source as (

    select * from {{ source('marketing', 'raw_referrals') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as referral_id,
        cast(referrer_customer_id as varchar) as referrer_customer_id,
        cast(referee_customer_id as varchar) as referee_customer_id,
        cast(campaign_id as varchar) as campaign_id,

        ---------- text
        status as referral_status,
        referral_code,

        ---------- numerics
        {{ cents_to_dollars('reward_amount') }} as reward_amount,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'referred_at') }} as referred_at,
        {{ dbt.date_trunc('day', 'converted_at') }} as converted_at

    from source

)

select * from renamed
