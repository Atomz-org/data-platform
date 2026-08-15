{{
    config(
        materialized='incremental',
        unique_key='email_event_id'
    )
}}

with

email_events as (

    select * from {{ ref('stg_email_events') }}
    {% if is_incremental() %}
    where event_at > (select max(event_at) from {{ this }})
    {% endif %}

)

select
    email_event_id,
    campaign_id,
    customer_id,
    email_event_type,
    event_at,
    event_date,
    {{ dbt.date_trunc('month', 'event_at') }} as event_month

from email_events
