with

email_touches as (

    select
        customer_id,
        event_date as touchpoint_date,
        'email' as channel,
        email_event_type as touchpoint_type,
        campaign_id
    from {{ ref('stg_email_events') }}

),

coupon_touches as (

    select
        customer_id,
        redeemed_at as touchpoint_date,
        'coupon' as channel,
        'redemption' as touchpoint_type,
        campaign_id
    from {{ ref('fct_coupon_redemptions') }}

),

social_touches as (

    select
        null as customer_id,
        posted_at as touchpoint_date,
        'social' as channel,
        platform as touchpoint_type,
        campaign_id
    from {{ ref('stg_social_media_posts') }}

),

all_touches as (

    select * from email_touches
    union all
    select * from coupon_touches
    union all
    select * from social_touches

),

final as (

    select
        customer_id,
        touchpoint_date,
        channel,
        touchpoint_type,
        campaign_id,
        row_number() over (
            partition by customer_id
            order by touchpoint_date
        ) as touchpoint_sequence
    from all_touches
    where customer_id is not null

)

select * from final
