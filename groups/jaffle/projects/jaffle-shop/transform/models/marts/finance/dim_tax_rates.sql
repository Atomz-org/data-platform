with

tax_rates as (

    select * from {{ ref('stg_tax_rates') }}

),

final as (

    select
        tax_rate_id,
        jurisdiction,
        tax_type,
        tax_rate_pct,
        effective_from_date,
        effective_to_date,
        case
            when effective_to_date is null
                or effective_to_date >= current_date
            then true
            else false
        end as is_current

    from tax_rates

)

select * from final
