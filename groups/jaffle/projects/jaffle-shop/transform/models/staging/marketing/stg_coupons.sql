with

source as (

    select * from {{ source('marketing', 'raw_coupons') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as coupon_id,
        cast(campaign_id as varchar) as campaign_id,

        ---------- text
        code as coupon_code,
        discount_type,
        status as coupon_status,

        ---------- numerics
        {{ cents_to_dollars('discount_amount') }} as discount_amount,
        discount_percent,
        {{ cents_to_dollars('minimum_order_amount') }} as minimum_order_amount,
        max_redemptions,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'valid_from') }} as valid_from,
        {{ dbt.date_trunc('day', 'valid_until') }} as valid_until,
        {{ dbt.date_trunc('day', 'created_at') }} as created_at

    from source

)

select * from renamed
