with

purchase_orders as (

    select * from {{ ref('stg_purchase_orders') }}

),

final as (

    select
        purchase_order_id,
        supplier_id,
        po_status,
        total_amount,
        created_at,
        ordered_at,
        case
            when ordered_at is not null and created_at is not null
                then {{ dbt.datediff('created_at', 'ordered_at', 'day') }}
            else null
        end as days_to_approval,
        case
            when ordered_at is not null and created_at is not null
                and {{ dbt.datediff('created_at', 'ordered_at', 'day') }} <= 1
                then 'same_day'
            when ordered_at is not null and created_at is not null
                and {{ dbt.datediff('created_at', 'ordered_at', 'day') }} <= 3
                then 'fast'
            when ordered_at is not null and created_at is not null
                and {{ dbt.datediff('created_at', 'ordered_at', 'day') }} <= 7
                then 'normal'
            when ordered_at is not null
                then 'slow'
            else 'pending'
        end as approval_speed
    from purchase_orders

)

select * from final
