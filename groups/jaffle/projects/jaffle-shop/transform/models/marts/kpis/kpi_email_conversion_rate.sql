with monthly as (
    select
        {{ sf_date_trunc('month', "event_date") }} as email_month,
        count(case when email_event_type = 'sent' then 1 end) as sent,
        count(case when email_event_type = 'opened' then 1 end) as opened,
        count(case when email_event_type = 'clicked' then 1 end) as clicked,
        count(case when email_event_type = 'converted' then 1 end) as converted
    from {{ ref('fct_email_events') }}
    group by 1
),
final as (
    select
        email_month,
        sent,
        opened,
        clicked,
        converted,
        round(opened * 100.0 / nullif(sent, 0), 2) as open_rate,
        round(clicked * 100.0 / nullif(opened, 0), 2) as click_to_open_rate,
        round(converted * 100.0 / nullif(sent, 0), 2) as conversion_rate
    from monthly
)
select * from final
