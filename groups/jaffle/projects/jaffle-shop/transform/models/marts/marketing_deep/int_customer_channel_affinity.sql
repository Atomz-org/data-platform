with

email_events as (

    select
        customer_id,
        'email' as channel,
        count(case when email_event_type in ('opened', 'clicked') then 1 end) as engagement_count
    from {{ ref('stg_email_events') }}
    group by 1

),

coupon_engagements as (

    select
        customer_id,
        'coupon' as channel,
        count(redemption_id) as engagement_count
    from {{ ref('stg_coupon_redemptions') }}
    group by 1

),

all_channels as (

    select * from email_events
    union all
    select * from coupon_engagements

),

customer_totals as (

    select
        customer_id,
        sum(engagement_count) as total_engagements
    from all_channels
    group by 1

),

channel_pct as (

    select
        ac.customer_id,
        ac.channel,
        ac.engagement_count,
        ct.total_engagements,
        case
            when ct.total_engagements > 0
                then round(cast(ac.engagement_count * 100.0 / ct.total_engagements as {{ dbt.type_float() }}), 2)
            else 0
        end as channel_pct
    from all_channels as ac
    inner join customer_totals as ct
        on ac.customer_id = ct.customer_id

),

preferred as (

    select
        customer_id,
        channel,
        engagement_count,
        total_engagements,
        channel_pct,
        row_number() over (
            partition by customer_id
            order by engagement_count desc
        ) as channel_rank
    from channel_pct

)

select * from preferred
