with

emails as (
    select * from {{ ref('stg_email_events') }}
),

campaigns as (
    select campaign_id, campaign_name, campaign_channel from {{ ref('stg_campaigns') }}
),

final as (
    select
        ee.email_event_id,
        ee.campaign_id,
        ca.campaign_name,
        ca.campaign_channel,
        ee.customer_id,
        ee.email_event_type,
        ee.event_date
    from emails as ee
    left join campaigns as ca on ee.campaign_id = ca.campaign_id
)

select * from final
