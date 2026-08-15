with

source as (

    select * from {{ source('finance', 'raw_tax_rates') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as tax_rate_id,

        ---------- text
        jurisdiction,
        tax_type,

        ---------- numerics
        rate as tax_rate_pct,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'effective_from') }} as effective_from_date,
        {{ dbt.date_trunc('day', 'effective_to') }} as effective_to_date

    from source

)

select * from renamed
