with

email_events as (

    select * from {{ ref('stg_email_events') }}

),

campaigns as (

    select
        campaign_id,
        campaign_name,
        campaign_channel
    from {{ ref('stg_campaigns') }}

),

send_counts as (

    select
        campaign_id,
        count(case when email_event_type = 'sent' then 1 end) as total_sent,
        count(case when email_event_type = 'unsubscribed' then 1 end) as total_unsubscribes,
        count(case when email_event_type = 'opened' then 1 end) as total_opens,
        count(case when email_event_type = 'clicked' then 1 end) as total_clicks
    from email_events
    group by 1

),

customer_send_frequency as (

    select
        customer_id,
        count(distinct campaign_id) as campaigns_received,
        count(case when email_event_type = 'unsubscribed' then 1 end) as unsubscribe_count
    from email_events
    group by 1

),

final as (

    select
        sc.campaign_id,
        c.campaign_name,
        sc.total_sent,
        sc.total_unsubscribes,
        sc.total_opens,
        sc.total_clicks,
        case
            when sc.total_sent > 0
                then round(cast(sc.total_unsubscribes * 100.0 / sc.total_sent as {{ dbt.type_float() }}), 2)
            else 0
        end as unsubscribe_rate_pct,
        case
            when sc.total_sent > 0
                then round(cast(sc.total_opens * 100.0 / sc.total_sent as {{ dbt.type_float() }}), 2)
            else 0
        end as open_rate_pct
    from send_counts as sc
    left join campaigns as c
        on sc.campaign_id = c.campaign_id

)

select * from final
