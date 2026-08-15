with

tax_by_jurisdiction as (

    select * from {{ ref('int_tax_collected_by_jurisdiction') }}

),

jurisdiction_summary as (

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
        case
            when taxable_amount > 0
                then (tax_collected / taxable_amount) - tax_rate_pct
            else null
        end as rate_variance

    from tax_by_jurisdiction

),

with_analysis as (

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
        effective_tax_rate,
        rate_variance,
        taxable_amount + tax_collected as total_with_tax,
        case
            when (taxable_amount + tax_collected) > 0
                then tax_collected / (taxable_amount + tax_collected)
            else 0
        end as tax_burden_pct,
        avg(effective_tax_rate) over (
            partition by jurisdiction, tax_type
        ) as avg_effective_rate_for_jurisdiction,
        sum(tax_collected) over (
            partition by jurisdiction, tax_type
            order by tax_month
            rows between unbounded preceding and current row
        ) as cumulative_tax_collected,
        rank() over (
            partition by tax_month
            order by tax_collected desc
        ) as jurisdiction_rank_by_tax

    from jurisdiction_summary

)

select * from with_analysis
