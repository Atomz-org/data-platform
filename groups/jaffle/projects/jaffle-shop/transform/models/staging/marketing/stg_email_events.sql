with

source as (

    select * from {{ source('marketing', 'raw_email_events') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as email_event_id,
        cast(campaign_id as varchar) as campaign_id,
        cast(customer_id as varchar) as customer_id,

        ---------- text
        event_type as email_event_type,
        email_subject,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'event_at') }} as event_date,
        event_at as event_at

    from source

)

select * from renamed
