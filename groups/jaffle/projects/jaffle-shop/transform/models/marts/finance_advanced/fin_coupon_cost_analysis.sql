with

cr as (
    select * from {{ ref('fct_coupon_redemptions') }}
),

redemptions as (

    select
        cr.coupon_id,
        cr.campaign_id,
        cr.discount_applied,
        cr.redeemed_at,
        {{ dbt.date_trunc('month', 'cr.redeemed_at') }} as redemption_month
    from cr

),

campaign_names as (

    select
        campaign_id,
        campaign_name,
        campaign_channel
    from {{ ref('dim_campaigns') }}

),

monthly_by_campaign as (

    select
        r.campaign_id,
        c.campaign_name,
        c.campaign_channel,
        r.redemption_month,
        count(*) as redemption_count,
        sum(r.discount_applied) as total_discount_cost,
        avg(r.discount_applied) as avg_discount_per_redemption,
        min(r.discount_applied) as min_discount,
        max(r.discount_applied) as max_discount
    from redemptions as r
    left join campaign_names as c
        on r.campaign_id = c.campaign_id
    group by 1, 2, 3, 4

),

final as (

    select
        campaign_id,
        campaign_name,
        campaign_channel,
        redemption_month,
        redemption_count,
        total_discount_cost,
        avg_discount_per_redemption,
        min_discount,
        max_discount,
        sum(total_discount_cost) over (
            partition by campaign_id order by redemption_month
        ) as cumulative_discount_cost
    from monthly_by_campaign

)

select * from final
