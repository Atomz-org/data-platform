with

members as (

    select
        loyalty_member_id,
        customer_id,
        enrolled_at
    from {{ ref('stg_loyalty_members') }}

),

first_txn as (

    select
        loyalty_member_id,
        min(transacted_at) as first_transaction_date
    from {{ ref('stg_loyalty_transactions') }}
    group by 1

),

final as (

    select
        m.loyalty_member_id,
        m.customer_id,
        m.enrolled_at,
        ft.first_transaction_date,
        case
            when ft.first_transaction_date is not null
                then {{ dbt.datediff('m.enrolled_at', 'ft.first_transaction_date', 'day') }}
            else null
        end as days_to_first_transaction,
        case
            when ft.first_transaction_date is null then 'not_activated'
            when {{ dbt.datediff('m.enrolled_at', 'ft.first_transaction_date', 'day') }} = 0 then 'same_day'
            when {{ dbt.datediff('m.enrolled_at', 'ft.first_transaction_date', 'day') }} <= 7 then 'first_week'
            when {{ dbt.datediff('m.enrolled_at', 'ft.first_transaction_date', 'day') }} <= 30 then 'first_month'
            else 'delayed_activation'
        end as activation_speed
    from members as m
    left join first_txn as ft
        on m.loyalty_member_id = ft.loyalty_member_id

)

select * from final
