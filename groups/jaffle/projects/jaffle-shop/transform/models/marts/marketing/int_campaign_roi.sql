with

campaign_spend as (

    select * from {{ ref('stg_campaign_spend') }}

),

campaign_orders as (

    select * from {{ ref('int_campaign_orders') }}

),

spend_by_campaign as (

    select
        campaign_id,
        sum(spend_amount) as total_spend,
        min(spend_date) as first_spend_date,
        max(spend_date) as last_spend_date,
        count(distinct spend_date) as days_with_spend

    from campaign_spend
    group by 1

),

revenue_by_campaign as (

    select
        campaign_id,
        campaign_name,
        campaign_channel,
        count(distinct order_id) as attributed_orders,
        count(distinct customer_id) as attributed_customers,
        sum(order_total) as attributed_revenue,
        sum(discount_applied) as total_discounts_given

    from campaign_orders
    group by 1, 2, 3

),

campaign_roi as (

    select
        coalesce(revenue_by_campaign.campaign_id, spend_by_campaign.campaign_id) as campaign_id,
        revenue_by_campaign.campaign_name,
        revenue_by_campaign.campaign_channel,
        coalesce(spend_by_campaign.total_spend, 0) as total_spend,
        coalesce(revenue_by_campaign.attributed_orders, 0) as attributed_orders,
        coalesce(revenue_by_campaign.attributed_customers, 0) as attributed_customers,
        coalesce(revenue_by_campaign.attributed_revenue, 0) as attributed_revenue,
        coalesce(revenue_by_campaign.total_discounts_given, 0) as total_discounts_given,
        case
            when coalesce(spend_by_campaign.total_spend, 0) > 0
            then (coalesce(revenue_by_campaign.attributed_revenue, 0) - spend_by_campaign.total_spend) / spend_by_campaign.total_spend
            else null
        end as roi_ratio,
        case
            when coalesce(revenue_by_campaign.attributed_orders, 0) > 0
            then coalesce(spend_by_campaign.total_spend, 0) / revenue_by_campaign.attributed_orders
            else null
        end as cost_per_order,
        spend_by_campaign.first_spend_date,
        spend_by_campaign.last_spend_date

    from revenue_by_campaign

    full outer join spend_by_campaign
        on revenue_by_campaign.campaign_id = spend_by_campaign.campaign_id

)

select * from campaign_roi
