with

tax_by_jurisdiction as (

    select * from {{ ref('int_tax_collected_by_jurisdiction') }}

),

final as (

    select
        jurisdiction,
        tax_type,
        tax_rate_pct,
        location_id,
        location_name,
        tax_month,
        invoice_count,
        taxable_amount,
        tax_collected,
        case
            when taxable_amount > 0
                then tax_collected / taxable_amount
            else 0
        end as effective_tax_rate,
        sum(tax_collected) over (
            partition by jurisdiction, tax_type
            order by tax_month
            rows between unbounded preceding and current row
        ) as cumulative_tax_collected

    from tax_by_jurisdiction

)

select * from final
