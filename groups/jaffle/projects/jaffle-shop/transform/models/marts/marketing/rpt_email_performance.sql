with

email_funnel as (

    select * from {{ ref('int_email_engagement_funnel') }}

),

final as (

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
        open_rate,
        click_through_rate,
        click_to_send_rate,
        unsubscribe_rate,
        bounce_rate,
        first_event_date,
        last_event_date,

        -- Deliverability
        total_sent - total_bounced as total_delivered,
        case
            when total_sent > 0
            then (total_sent - total_bounced) * 1.0 / total_sent
            else 0
        end as delivery_rate,

        -- Performance classification
        case
            when open_rate >= 0.30 then 'excellent'
            when open_rate >= 0.20 then 'good'
            when open_rate >= 0.10 then 'average'
            else 'poor'
        end as open_rate_tier,
        case
            when click_through_rate >= 0.10 then 'excellent'
            when click_through_rate >= 0.05 then 'good'
            when click_through_rate >= 0.02 then 'average'
            else 'poor'
        end as ctr_tier

    from email_funnel

)

select * from final
