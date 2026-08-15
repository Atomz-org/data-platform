with

coupons as (

    select * from {{ ref('stg_coupons') }}

),

final as (

    select
        coupon_id,
        coupon_code,
        campaign_id,
        discount_type,
        discount_amount,
        discount_percent,
        minimum_order_amount,
        max_redemptions,
        coupon_status,
        valid_from,
        valid_until,
        created_at,

        -- Derived fields
        case
            when discount_type = 'percentage' then discount_percent || '% off'
            when discount_type = 'fixed_amount' then '$' || discount_amount || ' off'
            else discount_type
        end as discount_description,
        case
            when coupon_status = 'active'
                and valid_from <= current_date
                and (valid_until >= current_date or valid_until is null)
            then true
            else false
        end as is_currently_valid

    from coupons

)

select * from final
