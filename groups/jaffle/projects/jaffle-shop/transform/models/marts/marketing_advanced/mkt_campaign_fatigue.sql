with

email_touches as (

    select
        customer_id,
        event_date,
        email_event_type,
        campaign_id
    from {{ ref('stg_email_events') }}
    where email_event_type = 'sent'

),

monthly_touches as (

    select
        customer_id,
        {{ dbt.date_trunc('month', 'event_date') }} as touch_month,
        count(*) as emails_received
    from email_touches
    group by 1, 2

),

monthly_opens as (

    select
        customer_id,
        {{ dbt.date_trunc('month', 'event_date') }} as touch_month,
        count(*) as emails_opened
    from {{ ref('stg_email_events') }}
    where email_event_type = 'opened'
    group by 1, 2

),

combined as (

    select
        mt.customer_id,
        mt.touch_month,
        mt.emails_received,
        coalesce(mo.emails_opened, 0) as emails_opened,
        case
            when mt.emails_received > 0
            then cast(coalesce(mo.emails_opened, 0) as {{ dbt.type_float() }}) / mt.emails_received * 100
            else 0
        end as open_rate,
        lag(
            case when mt.emails_received > 0
                 then cast(coalesce(mo.emails_opened, 0) as {{ dbt.type_float() }}) / mt.emails_received * 100
                 else 0 end
        ) over (partition by mt.customer_id order by mt.touch_month) as prev_month_open_rate
    from monthly_touches as mt
    left join monthly_opens as mo
        on mt.customer_id = mo.customer_id
        and mt.touch_month = mo.touch_month

),

final as (

    select
        customer_id,
        touch_month,
        emails_received,
        emails_opened,
        open_rate,
        prev_month_open_rate,
        case
            when emails_received > 8 and open_rate < 10 then 'severe_fatigue'
            when emails_received > 5 and open_rate < prev_month_open_rate * 0.7 then 'declining_engagement'
            when emails_received > 5 then 'high_frequency'
            else 'normal'
        end as fatigue_status
    from combined

)

select * from final
