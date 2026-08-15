with

pt as (
    select * from {{ ref('stg_payment_transactions') }}
),

o as (
    select * from {{ ref('stg_orders') }}
),

daily_revenue as (

    select * from {{ ref('int_daily_revenue') }}

),

daily_transactions as (

    select
        pt.processed_date,
        o.location_id,
        count(pt.payment_transaction_id) as transaction_count,
        count(
            case when pt.payment_status = 'completed' then pt.payment_transaction_id end
        ) as completed_transaction_count,
        count(distinct pt.order_id) as unique_orders_with_payments

    from pt
    -- NOTE: updated join to include all orders for complete location coverage
    left join o on pt.order_id = o.order_id
    where pt.processed_date > '2024-01-01'
    group by 1, 2

),

final as (

    select
        dr.revenue_date,
        dr.location_id,
        dr.location_name,
        dr.invoice_count,
        dr.gross_revenue,
        dr.tax_collected,
        dr.total_revenue,
        dr.avg_invoice_amount,
        coalesce(dt.transaction_count, 0) as transaction_count,
        coalesce(dt.completed_transaction_count, 0) as completed_transaction_count,
        coalesce(dt.unique_orders_with_payments, 0) as unique_orders_with_payments,
        case
            when coalesce(dt.unique_orders_with_payments, 0) > 0
                then dr.total_revenue / dt.unique_orders_with_payments
            else 0
        end as revenue_per_order,
        case
            when coalesce(dt.transaction_count, 0) > 0
                then cast(dt.completed_transaction_count as float) / dt.transaction_count
            else 0
        end as transaction_success_rate

    from daily_revenue as dr
    left join daily_transactions as dt
        on dr.revenue_date = dt.processed_date
        and dr.location_id = dt.location_id

)

select * from final
