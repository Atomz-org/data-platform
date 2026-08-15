with

refunds as (

    select * from {{ ref('stg_refunds') }}

),

final as (

    select
        refund_id,
        order_id,
        invoice_id,
        refund_reason,
        refund_status,
        refund_amount,
        requested_date,
        resolved_date,
        case
            when resolved_date is not null
                then {{ dbt.datediff('requested_date', 'resolved_date', 'day') }}
            else null
        end as processing_days,
        case
            when resolved_date is not null and {{ dbt.datediff('requested_date', 'resolved_date', 'day') }} <= 1
                then 'same_day'
            when resolved_date is not null and {{ dbt.datediff('requested_date', 'resolved_date', 'day') }} <= 3
                then 'fast'
            when resolved_date is not null and {{ dbt.datediff('requested_date', 'resolved_date', 'day') }} <= 7
                then 'normal'
            when resolved_date is not null
                then 'slow'
            else 'pending'
        end as processing_speed_tier
    from refunds

)

select * from final
