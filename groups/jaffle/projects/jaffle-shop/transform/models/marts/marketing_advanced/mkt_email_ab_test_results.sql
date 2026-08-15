with

email_events as (

    select
        email_event_id,
        customer_id,
        campaign_id,
        email_event_type,
        event_date,
        email_subject
    from {{ ref('stg_email_events') }}

),

variant_summary as (

    select
        campaign_id,
        coalesce(email_subject, 'control') as test_variant,
        count(case when email_event_type = 'sent' then 1 end) as sent_count,
        count(case when email_event_type = 'opened' then 1 end) as open_count,
        count(case when email_event_type = 'clicked' then 1 end) as click_count,
        count(case when email_event_type = 'unsubscribed' then 1 end) as unsub_count
    from email_events
    group by 1, 2

),

final as (

    select
        campaign_id,
        test_variant,
        sent_count,
        open_count,
        click_count,
        unsub_count,
        case when sent_count > 0 then cast(open_count as {{ dbt.type_float() }}) / sent_count * 100 else 0 end as open_rate_pct,
        case when sent_count > 0 then cast(click_count as {{ dbt.type_float() }}) / sent_count * 100 else 0 end as click_rate_pct,
        case when sent_count > 0 then cast(unsub_count as {{ dbt.type_float() }}) / sent_count * 100 else 0 end as unsub_rate_pct,
        rank() over (partition by campaign_id order by
            case when sent_count > 0 then cast(open_count as {{ dbt.type_float() }}) / sent_count else 0 end desc
        ) as open_rate_rank
    from variant_summary

)

select * from final
