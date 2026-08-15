with

email_events as (

    select * from {{ ref('stg_email_events') }}

),

campaigns as (

    select * from {{ ref('stg_campaigns') }}

),

final as (

    select
        email_events.email_event_id,
        email_events.campaign_id,
        email_events.customer_id,
        email_events.email_event_type,
        email_events.email_subject,
        email_events.event_date,
        email_events.event_at,

        -- Campaign context
        campaigns.campaign_name,
        campaigns.campaign_channel,
        campaigns.campaign_status,
        campaigns.campaign_start_date,
        campaigns.campaign_end_date,

        -- Boolean flags for easy filtering
        email_events.email_event_type = 'sent' as is_sent,
        email_events.email_event_type = 'opened' as is_opened,
        email_events.email_event_type = 'clicked' as is_clicked,
        email_events.email_event_type = 'unsubscribed' as is_unsubscribed,
        email_events.email_event_type = 'bounced' as is_bounced

    from email_events

    left join campaigns
        on email_events.campaign_id = campaigns.campaign_id

)

select * from final
