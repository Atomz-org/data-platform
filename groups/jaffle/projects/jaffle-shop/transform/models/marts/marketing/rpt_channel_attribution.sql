with

acquisition_source as (

    select * from {{ ref('int_customer_acquisition_source') }}

),

campaign_roi as (

    select * from {{ ref('int_campaign_roi') }}

),

-- Customers acquired per channel
channel_customers as (

    select
        coalesce(campaign_channel, acquisition_source) as channel,
        count(distinct customer_id) as customers_acquired

    from acquisition_source
    group by 1

),

-- Spend and revenue per channel from campaign ROI
channel_financials as (

    select
        campaign_channel as channel,
        sum(total_spend) as total_channel_spend,
        sum(attributed_revenue) as total_channel_revenue,
        sum(attributed_orders) as total_channel_orders,
        count(campaign_id) as campaigns_in_channel

    from campaign_roi
    where campaign_channel is not null
    group by 1

),

-- Combine
final as (

    select
        channel_customers.channel,
        channel_customers.customers_acquired,
        coalesce(channel_financials.total_channel_spend, 0) as total_spend,
        coalesce(channel_financials.total_channel_revenue, 0) as total_revenue,
        coalesce(channel_financials.total_channel_orders, 0) as total_orders,
        coalesce(channel_financials.campaigns_in_channel, 0) as campaign_count,

        -- Cost per acquisition
        case
            when channel_customers.customers_acquired > 0 and channel_financials.total_channel_spend is not null
            then channel_financials.total_channel_spend / channel_customers.customers_acquired
            else null
        end as cost_per_acquisition,

        -- Channel ROI
        case
            when coalesce(channel_financials.total_channel_spend, 0) > 0
            then (channel_financials.total_channel_revenue - channel_financials.total_channel_spend)
                / channel_financials.total_channel_spend
            else null
        end as channel_roi,

        -- Revenue per customer
        case
            when channel_customers.customers_acquired > 0
            then coalesce(channel_financials.total_channel_revenue, 0) / channel_customers.customers_acquired
            else null
        end as revenue_per_customer

    from channel_customers

    left join channel_financials
        on channel_customers.channel = channel_financials.channel

)

select * from final
