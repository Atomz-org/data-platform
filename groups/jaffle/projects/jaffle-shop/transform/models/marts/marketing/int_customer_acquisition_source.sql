with

customers as (

    select * from {{ ref('stg_customers') }}

),

referrals as (

    select * from {{ ref('stg_referrals') }}

),

campaigns as (

    select * from {{ ref('stg_campaigns') }}

),

coupon_redemptions as (

    select * from {{ ref('stg_coupon_redemptions') }}

),

coupons as (

    select * from {{ ref('stg_coupons') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

-- Find customers acquired through referrals
referral_acquisitions as (

    select
        referee_customer_id as customer_id,
        'referral' as acquisition_source,
        referrer_customer_id,
        referrals.campaign_id,
        referred_at as acquired_at

    from referrals
    where referral_status = 'converted'

),

-- Find first order per customer for campaign attribution
customer_first_orders as (

    select
        customer_id,
        order_id as first_order_id,
        ordered_at as first_order_date
    from (
        select
            customer_id,
            order_id,
            ordered_at,
            row_number() over (
                partition by customer_id
                order by ordered_at asc
            ) as rn
        from orders
    ) ranked
    where rn = 1

),

-- Find customers acquired through campaign coupons on their first order
campaign_acquisitions as (

    select
        customer_first_orders.customer_id,
        'campaign' as acquisition_source,
        cast(null as {{ dbt.type_string() }}) as referrer_customer_id,
        coupons.campaign_id,
        customer_first_orders.first_order_date as acquired_at

    from customer_first_orders

    inner join coupon_redemptions
        on customer_first_orders.first_order_id = coupon_redemptions.order_id
        and customer_first_orders.customer_id = coupon_redemptions.customer_id

    inner join coupons
        on coupon_redemptions.coupon_id = coupons.coupon_id
        and coupons.campaign_id is not null

),

-- Combine all attribution sources with first-touch priority
combined_sources as (

    select * from referral_acquisitions
    union all
    select * from campaign_acquisitions

),

-- Deduplicate: prefer referral over campaign (first-touch)
first_touch as (

    select
        customer_id,
        acquisition_source,
        referrer_customer_id,
        campaign_id,
        acquired_at
    from (
        select
            *,
            row_number() over (
                partition by customer_id
                order by
                    case acquisition_source
                        when 'referral' then 1
                        when 'campaign' then 2
                        else 3
                    end,
                    acquired_at asc
            ) as rn
        from combined_sources
    ) ranked
    where rn = 1

),

-- Join back to all customers to include organic
customer_acquisition as (

    select
        customers.customer_id,
        customers.customer_name,
        coalesce(first_touch.acquisition_source, 'organic') as acquisition_source,
        first_touch.referrer_customer_id,
        first_touch.campaign_id,
        campaigns.campaign_name,
        campaigns.campaign_channel,
        first_touch.acquired_at

    from customers

    left join first_touch
        on customers.customer_id = first_touch.customer_id

    left join campaigns
        on first_touch.campaign_id = campaigns.campaign_id

)

select * from customer_acquisition
