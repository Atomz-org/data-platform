with

coupons as (

    select * from {{ ref('dim_coupons') }}

),

coupon_redemptions as (

    select * from {{ ref('fct_coupon_redemptions') }}

),

-- Count redemptions per coupon
redemption_counts as (

    select
        coupon_id,
        count(redemption_id) as actual_redemptions,
        sum(discount_applied) as total_discount_used

    from coupon_redemptions
    group by 1

),

-- Coupons with upcoming or recent expiry
coupon_expiry as (

    select
        coupons.coupon_id,
        coupons.coupon_code,
        coupons.campaign_id,
        coupons.discount_type,
        coupons.discount_amount,
        coupons.discount_percent,
        coupons.discount_description,
        coupons.coupon_status,
        coupons.valid_from,
        coupons.valid_until,
        coupons.max_redemptions,
        coupons.is_currently_valid,
        coalesce(redemption_counts.actual_redemptions, 0) as actual_redemptions,
        coalesce(redemption_counts.total_discount_used, 0) as total_discount_used,
        -- Remaining redemptions
        case
            when coupons.max_redemptions is not null
            then coupons.max_redemptions - coalesce(redemption_counts.actual_redemptions, 0)
            else null
        end as remaining_redemptions,
        -- Days until expiry
        case
            when coupons.valid_until is not null
            then {{ dbt.datediff('current_date', 'coupons.valid_until', 'day') }}
            else null
        end as days_until_expiry,
        -- Expiry status
        case
            when coupons.valid_until is null then 'no_expiry'
            when coupons.valid_until < current_date then 'expired'
            when {{ dbt.datediff('current_date', 'coupons.valid_until', 'day') }} <= 7 then 'expiring_this_week'
            when {{ dbt.datediff('current_date', 'coupons.valid_until', 'day') }} <= 30 then 'expiring_this_month'
            when {{ dbt.datediff('current_date', 'coupons.valid_until', 'day') }} <= 90 then 'expiring_this_quarter'
            else 'long_term_valid'
        end as expiry_status,
        -- Estimated unused liability (for fixed amount coupons)
        case
            when coupons.discount_type = 'fixed_amount'
                and coupons.max_redemptions is not null
            then coupons.discount_amount
                * (coupons.max_redemptions - coalesce(redemption_counts.actual_redemptions, 0))
            else null
        end as estimated_unused_liability,
        -- Utilization rate
        case
            when coupons.max_redemptions is not null and coupons.max_redemptions > 0
            then coalesce(redemption_counts.actual_redemptions, 0) * 1.0 / coupons.max_redemptions
            else null
        end as utilization_rate

    from coupons

    left join redemption_counts
        on coupons.coupon_id = redemption_counts.coupon_id

)

select * from coupon_expiry
order by
    case expiry_status
        when 'expiring_this_week' then 1
        when 'expiring_this_month' then 2
        when 'expiring_this_quarter' then 3
        when 'long_term_valid' then 4
        when 'no_expiry' then 5
        when 'expired' then 6
    end,
    days_until_expiry
