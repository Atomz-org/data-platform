{{
    config(
        materialized='incremental',
        unique_key='redemption_id'
    )
}}

with

redemptions as (

    select * from {{ ref('stg_coupon_redemptions') }}
    {% if is_incremental() %}
    where redeemed_at > (select max(redeemed_at) from {{ this }})
    {% endif %}

)

select
    redemption_id,
    coupon_id,
    customer_id,
    order_id,
    redeemed_at,
    discount_applied,
    {{ dbt.date_trunc('day', 'redeemed_at') }} as redemption_date,
    {{ dbt.date_trunc('month', 'redeemed_at') }} as redemption_month

from redemptions
