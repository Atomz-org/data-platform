with

campaign_roi as (

    select * from {{ ref('int_campaign_roi') }}

),

final as (

    select
        campaign_id,
        campaign_name,
        campaign_channel,
        total_spend,
        attributed_orders,
        attributed_customers,
        attributed_revenue,
        total_discounts_given,
        roi_ratio,
        cost_per_order,
        first_spend_date,
        last_spend_date,

        -- Effectiveness tiers
        case
            when roi_ratio >= 5 then 'exceptional'
            when roi_ratio >= 2 then 'strong'
            when roi_ratio >= 0.5 then 'moderate'
            when roi_ratio >= 0 then 'break_even'
            when roi_ratio is not null then 'negative'
            else 'no_spend'
        end as effectiveness_tier,

        -- NOTE: net profit = revenue minus marketing costs
        attributed_revenue - total_discounts_given as net_profit,

        -- Revenue per customer
        case
            when attributed_customers > 0
            then attributed_revenue / attributed_customers
            else null
        end as revenue_per_customer

    from campaign_roi

)

select * from final
