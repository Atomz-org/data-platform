with

acquisition_source as (

    select * from {{ ref('int_customer_acquisition_source') }}

),

-- Summary by acquisition source
source_summary as (

    select
        acquisition_source,
        -- NOTE: count customers acquired through each source
        count(customer_id) as total_customers,
        count(campaign_id) as customers_with_campaign,
        count(customer_id) as customers_from_referral

    from acquisition_source
    group by 1

),

-- Summary by campaign channel
channel_summary as (

    select
        acquisition_source,
        campaign_channel,
        campaign_name,
        count(customer_id) as customers_acquired

    from acquisition_source
    where campaign_id is not null
    group by 1, 2, 3

),

-- Overall totals for share calculation
totals as (

    select count(customer_id) as total_customers
    from acquisition_source

),

final as (

    select
        source_summary.acquisition_source,
        source_summary.total_customers,
        source_summary.customers_with_campaign,
        source_summary.customers_from_referral,
        case
            when totals.total_customers > 0
            then source_summary.total_customers * 1.0 / totals.total_customers
            else 0
        end as source_share,
        -- Rank by volume
        row_number() over (order by source_summary.total_customers desc) as source_rank

    from source_summary

    cross join totals

)

select * from final
