with

tax_collected as (

    select
        jurisdiction,
        tax_month,
        tax_collected,
        taxable_amount,
        case when taxable_amount > 0 then tax_collected / taxable_amount else 0 end as effective_tax_rate
    from {{ ref('int_tax_collected_by_jurisdiction') }}

),

statutory_rates as (

    select
        jurisdiction,
        tax_rate_pct as statutory_rate
    from {{ ref('stg_tax_rates') }}
    where effective_to_date is null or effective_to_date >= current_date

),

final as (

    select
        tc.jurisdiction,
        tc.tax_month,
        tc.tax_collected,
        tc.taxable_amount,
        case when tc.taxable_amount > 0 then tc.tax_collected / tc.taxable_amount else 0 end,
        sr.statutory_rate,
        case when tc.taxable_amount > 0 then tc.tax_collected / tc.taxable_amount else 0 end - sr.statutory_rate as rate_gap,
        abs(case when tc.taxable_amount > 0 then tc.tax_collected / tc.taxable_amount else 0 end - sr.statutory_rate) * tc.taxable_amount as implied_tax_leakage,
        case
            when abs(case when tc.taxable_amount > 0 then tc.tax_collected / tc.taxable_amount else 0 end - sr.statutory_rate) > 0.02 then 'significant_gap'
            when abs(case when tc.taxable_amount > 0 then tc.tax_collected / tc.taxable_amount else 0 end - sr.statutory_rate) > 0.005 then 'minor_gap'
            else 'aligned'
        end as efficiency_status
    from tax_collected as tc
    left join statutory_rates as sr
        on tc.jurisdiction = sr.jurisdiction

)

select * from final
