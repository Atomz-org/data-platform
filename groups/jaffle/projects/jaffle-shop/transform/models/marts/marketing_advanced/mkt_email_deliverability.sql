with

emails as (

    select
        email_event_id,
        customer_id,
        campaign_id,
        email_event_type,
        event_date
    from {{ ref('stg_email_events') }}

),

campaign_summary as (

    select
        campaign_id,
        count(case when email_event_type = 'sent' then 1 end) as total_sent,
        count(case when email_event_type = 'delivered' then 1 end) as total_delivered,
        count(case when email_event_type = 'bounced' then 1 end) as total_bounced,
        count(case when email_event_type = 'opened' then 1 end) as total_opened,
        count(case when email_event_type = 'clicked' then 1 end) as total_clicked,
        count(case when email_event_type = 'unsubscribed' then 1 end) as total_unsubscribed,
        count(case when email_event_type = 'spam_reported' then 1 end) as total_spam
    from emails
    group by 1

),

final as (

    select
        campaign_id,
        total_sent,
        total_delivered,
        total_bounced,
        total_opened,
        total_clicked,
        total_unsubscribed,
        total_spam,
        case when total_sent > 0 then cast(total_delivered as {{ dbt.type_float() }}) / total_sent * 100 else 0 end as delivery_rate_pct,
        case when total_sent > 0 then cast(total_bounced as {{ dbt.type_float() }}) / total_sent * 100 else 0 end as bounce_rate_pct,
        case when total_sent > 0 then cast(total_spam as {{ dbt.type_float() }}) / total_sent * 100 else 0 end as spam_rate_pct,
        case when total_delivered > 0 then cast(total_opened as {{ dbt.type_float() }}) / total_delivered * 100 else 0 end as open_rate_pct,
        case when total_opened > 0 then cast(total_clicked as {{ dbt.type_float() }}) / total_opened * 100 else 0 end as click_to_open_rate_pct
    from campaign_summary

)

select * from final
