with

refunds_enriched as (

    select * from {{ ref('int_refunds_enriched') }}

),

invoices as (

    select
        invoice_id,
        order_id,
        issued_date,
        total_amount

    from {{ ref('stg_invoices') }}
    where invoice_status != 'draft'

),

orders as (

    select
        order_id,
        location_id

    from {{ ref('stg_orders') }}

),

monthly_refunds as (

    select
        re.location_id,
        {{ dbt.date_trunc('month', 're.requested_date') }} as refund_month,
        count(re.refund_id) as refund_count,
        sum(re.refund_amount) as total_refund_amount,
        avg(re.refund_amount) as avg_refund_amount,
        count(case when re.refund_status = 'approved' then 1 end) as approved_refund_count,
        avg(re.days_to_resolution)::numeric as avg_days_to_resolution

    from refunds_enriched as re
    group by 1, 2

),

monthly_invoices as (

    select
        o.location_id,
        {{ dbt.date_trunc('month', 'inv.issued_date') }} as invoice_month,
        count(inv.invoice_id) as invoice_count,
        sum(inv.total_amount) as total_invoice_amount

    from invoices as inv
    inner join orders as o
        on inv.order_id = o.order_id
    group by 1, 2

),

refund_rates as (

    select
        mi.location_id,
        mi.invoice_month as report_month,
        mi.invoice_count,
        mi.total_invoice_amount,
        coalesce(mr.refund_count, 0) as refund_count,
        coalesce(mr.total_refund_amount, 0) as total_refund_amount,
        coalesce(mr.avg_refund_amount, 0) as avg_refund_amount,
        coalesce(mr.approved_refund_count, 0) as approved_refund_count,
        coalesce(mr.avg_days_to_resolution, 0) as avg_days_to_resolution,
        case
            when mi.invoice_count > 0
                then coalesce(mr.refund_count, 0)::float / mi.invoice_count
            else 0
        end as refund_rate,
        case
            when mi.total_invoice_amount > 0
                then coalesce(mr.total_refund_amount, 0) / mi.total_invoice_amount
            else 0
        end as refund_amount_rate

    from monthly_invoices as mi
    left join monthly_refunds as mr
        on mi.location_id = mr.location_id
        and mi.invoice_month = mr.refund_month

)

select * from refund_rates
