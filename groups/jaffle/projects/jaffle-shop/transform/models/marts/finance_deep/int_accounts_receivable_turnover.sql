with

ar as (

    select * from {{ ref('stg_accounts_receivable') }}

),

invoices as (

    select * from {{ ref('stg_invoices') }}

),

monthly_credit_sales as (

    select
        {{ dbt.date_trunc('month', 'issued_date') }} as sales_month,
        sum(total_amount) as net_credit_sales
    from invoices
    where invoice_status != 'draft'
    group by 1

),

monthly_ar_balance as (

    select
        {{ dbt.date_trunc('month', 'created_date') }} as ar_month,
        avg(amount_outstanding) as avg_ar_balance,
        sum(amount_outstanding) as total_ar_outstanding,
        count(receivable_id) as ar_count
    from ar
    group by 1

),

final as (

    select
        cs.sales_month,
        cs.net_credit_sales,
        coalesce(arb.avg_ar_balance, 0) as avg_ar_balance,
        coalesce(arb.total_ar_outstanding, 0) as total_ar_outstanding,
        arb.ar_count,
        case
            when coalesce(arb.avg_ar_balance, 0) > 0
                then round(cast(cs.net_credit_sales / arb.avg_ar_balance as {{ dbt.type_float() }}), 2)
            else null
        end as ar_turnover_ratio,
        case
            when cs.net_credit_sales > 0 and coalesce(arb.avg_ar_balance, 0) > 0
                then round(cast(365.0 * arb.avg_ar_balance / cs.net_credit_sales as {{ dbt.type_float() }}), 1)
            else null
        end as days_sales_outstanding
    from monthly_credit_sales as cs
    left join monthly_ar_balance as arb
        on cs.sales_month = arb.ar_month

)

select * from final
