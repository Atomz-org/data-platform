with

monthly_email as (
    select
        {{ sf_date_trunc('month', "event_date") }} as email_month,
        count(case when email_event_type = 'sent' then 1 end) as sent,
        count(case when email_event_type = 'opened' then 1 end) as opened,
        count(case when email_event_type = 'clicked' then 1 end) as clicked
    from {{ ref('fct_email_events') }}
    group by 1
),

with_rates as (
    select
        email_month,
        sent,
        opened,
        clicked,
        round(opened * 100.0 / nullif(sent, 0), 2) as open_rate,
        round(clicked * 100.0 / nullif(opened, 0), 2) as ctr
    from monthly_email
),

compared as (
    select
        email_month,
        open_rate as current_open_rate,
        lag(open_rate) over (order by email_month) as prior_month_open_rate,
        open_rate - lag(open_rate) over (order by email_month) as open_rate_change_pp,
        ctr as current_ctr,
        lag(ctr) over (order by email_month) as prior_month_ctr,
        sent as current_sent,
        lag(sent) over (order by email_month) as prior_month_sent
    from with_rates
)

select * from compared
