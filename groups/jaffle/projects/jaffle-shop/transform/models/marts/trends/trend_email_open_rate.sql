with

daily_emails as (
    select
        event_date,
        count(case when email_event_type = 'sent' then 1 end) as sent_count,
        count(case when email_event_type = 'opened' then 1 end) as open_count,
        count(case when email_event_type = 'clicked' then 1 end) as click_count
    from {{ ref('fct_email_events') }}
    group by 1
),

trended as (
    select
        event_date,
        sent_count,
        open_count,
        click_count,
        round(open_count * 100.0 / nullif(sent_count, 0), 2) as open_rate_pct,
        round(click_count * 100.0 / nullif(open_count, 0), 2) as click_to_open_rate_pct,
        avg(round(open_count * 100.0 / nullif(sent_count, 0), 2)) over (
            order by event_date rows between 6 preceding and current row
        ) as open_rate_7d_ma,
        avg(round(open_count * 100.0 / nullif(sent_count, 0), 2)) over (
            order by event_date rows between 27 preceding and current row
        ) as open_rate_28d_ma
    from daily_emails
)

select * from trended
