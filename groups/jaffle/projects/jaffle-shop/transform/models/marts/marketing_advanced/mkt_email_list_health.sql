with

customers as (

    select
        customer_id,
        customer_name
    from {{ ref('stg_customers') }}

),

email_activity as (

    select
        customer_id,
        max(event_date) as last_email_date,
        max(case when email_event_type = 'opened' then event_date end) as last_open_date,
        max(case when email_event_type = 'bounced' then event_date end) as last_bounce_date,
        max(case when email_event_type = 'unsubscribed' then event_date end) as unsubscribe_date,
        count(case when email_event_type = 'opened' then 1 end) as total_opens,
        count(case when email_event_type = 'bounced' then 1 end) as total_bounces
    from {{ ref('stg_email_events') }}
    group by 1

),

final as (

    select
        c.customer_id,
        ea.last_email_date,
        ea.last_open_date,
        ea.unsubscribe_date,
        ea.total_opens,
        ea.total_bounces,
        case
            when ea.unsubscribe_date is not null then 'unsubscribed'
            when ea.total_bounces > 3 then 'hard_bounce'
            when ea.last_open_date is null then 'never_engaged'
            when {{ dbt.datediff('ea.last_open_date', 'current_date', 'day') }} > 180 then 'inactive'
            when {{ dbt.datediff('ea.last_open_date', 'current_date', 'day') }} > 90 then 'at_risk'
            else 'active'
        end as subscriber_status
    from customers as c
    left join email_activity as ea on c.customer_id = ea.customer_id

)

select * from final
