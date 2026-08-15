with

invoices as (

    select * from {{ ref('stg_invoices') }}

),

payments as (

    select * from {{ ref('stg_payment_transactions') }}

),

payment_totals as (

    select
        order_id,
        sum(case when payment_status = 'completed' then payment_amount else 0 end) as total_paid,
        count(payment_transaction_id) as payment_count
    from payments
    group by 1

),

matched as (

    select
        i.invoice_id,
        i.order_id,
        i.total_amount as invoice_amount,
        coalesce(pt.total_paid, 0) as total_paid,
        coalesce(pt.payment_count, 0) as payment_count,
        coalesce(pt.total_paid, 0) - i.total_amount as payment_variance,
        case
            when coalesce(pt.total_paid, 0) = 0 then 'unpaid'
            when coalesce(pt.total_paid, 0) < i.total_amount then 'underpaid'
            when coalesce(pt.total_paid, 0) = i.total_amount then 'fully_paid'
            else 'overpaid'
        end as payment_match_status
    from invoices as i
    left join payment_totals as pt
        on i.order_id = pt.order_id

)

select * from matched
