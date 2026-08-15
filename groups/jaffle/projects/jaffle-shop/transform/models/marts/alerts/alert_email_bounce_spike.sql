with

daily_emails as (
    select
        event_date,
        count(case when email_event_type = 'sent' then 1 end) as sent,
        count(case when email_event_type = 'bounced' then 1 end) as bounced,
        round(count(case when email_event_type = 'bounced' then 1 end) * 100.0
            / nullif(count(case when email_event_type = 'sent' then 1 end), 0), 2) as bounce_rate_pct
    from {{ ref('fct_email_events') }}
    group by 1
),

alerts as (
    select
        event_date,
        sent,
        bounced,
        bounce_rate_pct,
        'email_bounce_spike' as alert_type,
        case when bounce_rate_pct > 15 then 'critical' else 'warning' end as severity
    from daily_emails
    where bounce_rate_pct > 5
)

select * from alerts
