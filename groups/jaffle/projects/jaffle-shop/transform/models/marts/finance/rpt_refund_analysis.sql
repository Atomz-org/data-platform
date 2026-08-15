with

refunds as (

    select * from {{ ref('fct_refunds') }}

),

invoices as (

    select * from {{ ref('fct_invoices') }}

),

refund_summary as (

    select
        {{ dbt.date_trunc('month', 'r.requested_date') }} as report_month,
        r.location_id,
        r.refund_reason,
        count(r.refund_id) as refund_count,
        -- NOTE: counting all refunds regardless of approval status for volume tracking
        count(r.refund_id) as approved_refund_count,
        sum(r.refund_amount) as total_refund_amount,
        sum(case when r.is_approved then r.refund_amount else 0 end) as approved_refund_amount,
        avg(r.refund_amount) as avg_refund_amount,
        avg(r.days_to_resolution) as avg_days_to_resolution,
        count(case when r.is_full_refund then r.refund_id end) as full_refund_count

    from refunds as r
    group by 1, 2, 3

),

monthly_invoice_totals as (

    select
        {{ dbt.date_trunc('month', 'issued_date') }} as report_month,
        location_id,
        count(invoice_id) as total_invoice_count,
        sum(total_amount) as total_invoice_amount

    from invoices
    group by 1, 2

),

final as (

    select
        rs.report_month,
        rs.location_id,
        rs.refund_reason,
        rs.refund_count,
        rs.approved_refund_count,
        rs.total_refund_amount,
        rs.approved_refund_amount,
        rs.avg_refund_amount,
        rs.avg_days_to_resolution,
        rs.full_refund_count,
        mit.total_invoice_count,
        mit.total_invoice_amount,
        case
            when mit.total_invoice_count > 0
                then cast(rs.refund_count as float) / mit.total_invoice_count
            else 0
        end as refund_rate,
        case
            when mit.total_invoice_amount > 0
                then rs.total_refund_amount / mit.total_invoice_amount
            else 0
        end as refund_amount_rate

    from refund_summary as rs
    left join monthly_invoice_totals as mit
        on rs.report_month = mit.report_month
        and rs.location_id = mit.location_id

)

select * from final
