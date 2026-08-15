with

source as (

    select * from {{ source('marketing', 'raw_campaigns') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as campaign_id,

        ---------- text
        name as campaign_name,
        channel as campaign_channel,
        status as campaign_status,
        description as campaign_description,

        ---------- numerics
        {{ cents_to_dollars('budget') }} as budget,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'start_date') }} as campaign_start_date,
        {{ dbt.date_trunc('day', 'end_date') }} as campaign_end_date,
        {{ dbt.date_trunc('day', 'created_at') }} as created_at

    from source

)

select * from renamed
