with

source as (

    select * from {{ source('marketing', 'raw_campaign_spend') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as campaign_spend_id,
        cast(campaign_id as varchar) as campaign_id,

        ---------- text
        channel as spend_channel,

        ---------- numerics
        {{ cents_to_dollars('amount') }} as spend_amount,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'spend_date') }} as spend_date

    from source

)

select * from renamed
