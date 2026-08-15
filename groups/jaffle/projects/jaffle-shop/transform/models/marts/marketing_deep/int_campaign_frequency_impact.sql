with

email_events as (

    select * from {{ ref('stg_email_events') }}

),

customer_send_history as (

    select
        customer_id,
        {{ dbt.date_trunc('month', 'event_date') }} as send_month,
        count(case when email_event_type = 'sent' then 1 end) as emails_sent,
        count(case when email_event_type = 'opened' then 1 end) as emails_opened,
        count(case when email_event_type = 'clicked' then 1 end) as emails_clicked,
        count(case when email_event_type = 'unsubscribed' then 1 end) as unsubscribes
    from email_events
    group by 1, 2

),

final as (

    select
        send_month,
        case
            when emails_sent <= 2 then 'low_frequency'
            when emails_sent <= 5 then 'moderate_frequency'
            else 'high_frequency'
        end as send_frequency_tier,
        count(distinct customer_id) as customer_count,
        avg(emails_sent) as avg_emails_sent,
        avg(case when emails_sent > 0 then emails_opened * 100.0 / emails_sent else 0 end) as avg_open_rate,
        avg(case when emails_sent > 0 then emails_clicked * 100.0 / emails_sent else 0 end) as avg_click_rate,
        sum(unsubscribes) as total_unsubscribes,
        avg(case when emails_sent > 0 then unsubscribes * 100.0 / emails_sent else 0 end) as avg_unsubscribe_rate
    from customer_send_history
    group by 1, 2

)

select * from final
