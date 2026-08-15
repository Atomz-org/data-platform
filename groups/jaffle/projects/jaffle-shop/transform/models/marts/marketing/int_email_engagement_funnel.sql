with

email_events as (

    select * from {{ ref('stg_email_events') }}

),

-- Aggregate email events by campaign
campaign_email_stats as (

    select
        campaign_id,
        email_subject,
        count(case when email_event_type = 'sent' then 1 end) as total_sent,
        count(case when email_event_type = 'opened' then 1 end) as total_opened,
        count(case when email_event_type = 'clicked' then 1 end) as total_clicked,
        count(case when email_event_type = 'unsubscribed' then 1 end) as total_unsubscribed,
        count(case when email_event_type = 'bounced' then 1 end) as total_bounced,
        count(distinct case when email_event_type = 'sent' then customer_id end) as unique_recipients,
        count(distinct case when email_event_type = 'opened' then customer_id end) as unique_openers,
        count(distinct case when email_event_type = 'clicked' then customer_id end) as unique_clickers,
        min(event_date) as first_event_date,
        max(event_date) as last_event_date

    from email_events
    group by 1, 2

),

-- Calculate funnel conversion rates
email_funnel as (

    select
        campaign_id,
        email_subject,
        total_sent,
        total_opened,
        total_clicked,
        total_unsubscribed,
        total_bounced,
        unique_recipients,
        unique_openers,
        unique_clickers,
        case
            when total_sent > 0
            then total_opened * 1.0 / total_sent
            else 0
        end as open_rate,
        case
            when total_opened > 0
            then total_clicked * 1.0 / total_opened
            else 0
        end as click_through_rate,
        case
            when total_sent > 0
            then total_clicked * 1.0 / total_sent
            else 0
        end as click_to_send_rate,
        case
            when total_sent > 0
            then total_unsubscribed * 1.0 / total_sent
            else 0
        end as unsubscribe_rate,
        case
            when total_sent > 0
            then total_bounced * 1.0 / total_sent
            else 0
        end as bounce_rate,
        first_event_date,
        last_event_date

    from campaign_email_stats

)

select * from email_funnel
