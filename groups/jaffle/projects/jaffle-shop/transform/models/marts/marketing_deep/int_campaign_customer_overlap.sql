with

email_events as (

    select * from {{ ref('stg_email_events') }}

),

campaigns as (

    select
        campaign_id,
        campaign_name,
        campaign_start_date,
        campaign_end_date
    from {{ ref('stg_campaigns') }}

),

customer_campaign as (

    select distinct
        ee.customer_id,
        ee.campaign_id
    from email_events as ee
    where ee.email_event_type = 'sent'

),

customer_campaign_count as (

    select
        customer_id,
        count(distinct campaign_id) as campaigns_targeted
    from customer_campaign
    group by 1

),

overlap_summary as (

    select
        campaigns_targeted,
        count(distinct customer_id) as customer_count,
        case
            when campaigns_targeted = 1 then 'single_campaign'
            when campaigns_targeted <= 3 then 'moderate_overlap'
            else 'high_overlap'
        end as overlap_tier
    from customer_campaign_count
    group by 1

)

select * from overlap_summary
