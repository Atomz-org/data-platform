with

campaigns as (

    select
        campaign_id,
        campaign_name,
        campaign_channel,
        campaign_start_date,
        campaign_end_date,
        'campaign' as promo_source
    from {{ ref('dim_campaigns') }}

),

coupons as (

    select
        coupon_id as promo_id,
        coupon_code as promo_name,
        discount_type as promo_type,
        valid_from as campaign_start_date,
        valid_until as campaign_end_date,
        'coupon' as promo_source
    from {{ ref('dim_coupons') }}

),

all_promos as (

    select
        campaign_id as promo_id,
        campaign_name as promo_name,
        campaign_channel as promo_type,
        campaign_start_date,
        campaign_end_date,
        promo_source
    from campaigns
    union all
    select * from coupons

),

overlap_count as (

    select
        a.promo_id,
        a.promo_name,
        a.promo_type,
        a.campaign_start_date,
        a.campaign_end_date,
        a.promo_source,
        count(distinct b.promo_id) - 1 as concurrent_promos,
        {{ dbt.datediff('a.campaign_start_date', 'a.campaign_end_date', 'day') }} as promo_duration_days
    from all_promos as a
    left join all_promos as b
        on a.campaign_start_date <= b.campaign_end_date
        and a.campaign_end_date >= b.campaign_start_date
    group by 1, 2, 3, 4, 5, 6

),

final as (

    select
        promo_id,
        promo_name,
        promo_type,
        campaign_start_date,
        campaign_end_date,
        promo_source,
        promo_duration_days,
        concurrent_promos,
        case
            when concurrent_promos > 3 then 'heavy_overlap'
            when concurrent_promos > 1 then 'moderate_overlap'
            when concurrent_promos > 0 then 'minor_overlap'
            else 'no_overlap'
        end as overlap_flag
    from overlap_count

)

select * from final
