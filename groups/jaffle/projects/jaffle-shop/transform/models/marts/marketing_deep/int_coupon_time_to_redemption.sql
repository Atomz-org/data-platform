with

coupons as (

    select
        coupon_id,
        campaign_id,
        coupon_code,
        discount_type,
        valid_from,
        valid_until
    from {{ ref('stg_coupons') }}

),

redemptions as (

    select
        coupon_id,
        min(redeemed_at) as first_redemption_date,
        count(redemption_id) as total_redemptions
    from {{ ref('stg_coupon_redemptions') }}
    group by 1

),

final as (

    select
        c.coupon_id,
        c.coupon_code,
        c.discount_type,
        c.valid_from,
        c.valid_until,
        r.first_redemption_date,
        r.total_redemptions,
        case
            when r.first_redemption_date is not null
                then {{ dbt.datediff('c.valid_from', 'r.first_redemption_date', 'day') }}
            else null
        end as days_to_first_redemption,
        case
            when r.first_redemption_date is null then 'unredeemed'
            when {{ dbt.datediff('c.valid_from', 'r.first_redemption_date', 'day') }} <= 1 then 'immediate'
            when {{ dbt.datediff('c.valid_from', 'r.first_redemption_date', 'day') }} <= 7 then 'first_week'
            when {{ dbt.datediff('c.valid_from', 'r.first_redemption_date', 'day') }} <= 30 then 'first_month'
            else 'delayed'
        end as redemption_speed
    from coupons as c
    left join redemptions as r
        on c.coupon_id = r.coupon_id

)

select * from final
