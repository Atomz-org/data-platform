with

source as (

    select * from {{ source('marketing', 'raw_coupon_redemptions') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as redemption_id,
        cast(coupon_id as varchar) as coupon_id,
        cast(order_id as varchar) as order_id,
        cast(customer_id as varchar) as customer_id,

        ---------- numerics
        {{ cents_to_dollars('discount_applied') }} as discount_applied,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'redeemed_at') }} as redeemed_at

    from source

)

select * from renamed
