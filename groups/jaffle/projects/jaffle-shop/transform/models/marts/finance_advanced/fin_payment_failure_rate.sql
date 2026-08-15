with

transactions as (

    select
        payment_transaction_id,
        order_id,
        payment_method,
        payment_status,
        payment_amount,
        processed_date
    from {{ ref('stg_payment_transactions') }}

),

daily_summary as (

    select
        processed_date,
        payment_method,
        count(*) as total_attempts,
        sum(case when payment_status = 'completed' then 1 else 0 end) as successful,
        sum(case when payment_status = 'failed' then 1 else 0 end) as failed,
        sum(case when payment_status = 'declined' then 1 else 0 end) as declined,
        sum(case when payment_status not in ('completed', 'failed', 'declined') then 1 else 0 end) as other_status,
        sum(case when payment_status in ('failed', 'declined') then payment_amount else 0 end) as failed_amount,
        sum(payment_amount) as total_attempted_amount
    from transactions
    group by 1, 2

),

final as (

    select
        processed_date,
        payment_method,
        total_attempts,
        successful,
        failed,
        declined,
        other_status,
        failed_amount,
        total_attempted_amount,
        case
            when total_attempts > 0
            then cast(failed + declined as {{ dbt.type_float() }}) / total_attempts * 100
            else 0
        end as failure_rate_pct,
        case
            when total_attempted_amount > 0
            then failed_amount / total_attempted_amount * 100
            else 0
        end as failed_amount_pct
    from daily_summary

)

select * from final
