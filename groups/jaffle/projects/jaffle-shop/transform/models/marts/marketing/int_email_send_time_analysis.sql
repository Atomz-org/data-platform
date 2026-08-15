with

email_events as (

    select * from {{ ref('stg_email_events') }}

),

-- Extract hour and day of week from send events
send_events as (

    select
        email_event_id,
        campaign_id,
        customer_id,
        email_subject,
        event_at,
        {{ dbt.date_trunc('hour', 'event_at') }} as event_hour,
        extract(hour from event_at) as hour_of_day,
        {{ day_of_week_number('event_at') }} as day_of_week

    from email_events
    where email_event_type = 'sent'

),

-- Match opens and clicks back to their send time
open_events as (

    select
        customer_id,
        campaign_id,
        email_subject
    from email_events
    where email_event_type = 'opened'

),

click_events as (

    select
        customer_id,
        campaign_id,
        email_subject
    from email_events
    where email_event_type = 'clicked'

),

-- Aggregate by hour of day and day of week
time_slot_stats as (

    select
        send_events.hour_of_day,
        send_events.day_of_week,
        count(send_events.email_event_id) as total_sent,
        count(distinct open_events.customer_id) as total_opened,
        count(distinct click_events.customer_id) as total_clicked,
        case
            when count(send_events.email_event_id) > 0
            then count(distinct open_events.customer_id) * 1.0 / count(send_events.email_event_id)
            else 0
        end as open_rate,
        case
            when count(distinct open_events.customer_id) > 0
            then count(distinct click_events.customer_id) * 1.0 / count(distinct open_events.customer_id)
            else 0
        end as click_rate,
        case
            when count(send_events.email_event_id) > 0
            then count(distinct click_events.customer_id) * 1.0 / count(send_events.email_event_id)
            else 0
        end as click_to_send_rate

    from send_events

    left join open_events
        on send_events.customer_id = open_events.customer_id
        and send_events.campaign_id = open_events.campaign_id
        and send_events.email_subject = open_events.email_subject

    left join click_events
        on send_events.customer_id = click_events.customer_id
        and send_events.campaign_id = click_events.campaign_id
        and send_events.email_subject = click_events.email_subject

    group by 1, 2

)

select * from time_slot_stats
