with

email_engagement as (

    select
        customer_id,
        count(case when email_event_type = 'sent' then 1 end) as emails_sent,
        count(case when email_event_type = 'opened' then 1 end) as emails_opened,
        case
            when count(case when email_event_type = 'sent' then 1 end) > 0
            then cast(count(case when email_event_type = 'opened' then 1 end) as {{ dbt.type_float() }})
                / count(case when email_event_type = 'sent' then 1 end) * 100
            else 0
        end as email_open_rate
    from {{ ref('stg_email_events') }}
    group by 1

),

coupon_engagement as (

    select
        customer_id,
        count(*) as coupons_redeemed,
        sum(discount_applied) as total_discount
    from {{ ref('fct_coupon_redemptions') }}
    group by 1

),

final as (

    select
        coalesce(ee.customer_id, ce.customer_id) as customer_id,
        coalesce(ee.emails_sent, 0) as emails_sent,
        coalesce(ee.emails_opened, 0) as emails_opened,
        coalesce(ee.email_open_rate, 0) as email_open_rate,
        coalesce(ce.coupons_redeemed, 0) as coupons_redeemed,
        case
            when coalesce(ee.email_open_rate, 0) > 30 and coalesce(ce.coupons_redeemed, 0) > 2 then 'multi_channel_responsive'
            when coalesce(ee.email_open_rate, 0) > 30 then 'email_preferred'
            when coalesce(ce.coupons_redeemed, 0) > 2 then 'coupon_preferred'
            else 'low_responsiveness'
        end as preferred_channel
    from email_engagement as ee
    full outer join coupon_engagement as ce
        on ee.customer_id = ce.customer_id

)

select * from final
