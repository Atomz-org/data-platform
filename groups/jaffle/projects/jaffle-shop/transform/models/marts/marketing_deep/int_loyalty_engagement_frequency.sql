with

loyalty_txns as (

    select * from {{ ref('stg_loyalty_transactions') }}

),

member_txn_gaps as (

    select
        loyalty_member_id,
        transacted_at,
        lag(transacted_at) over (
            partition by loyalty_member_id
            order by transacted_at
        ) as prev_transaction_date,
        case
            when lag(transacted_at) over (
                partition by loyalty_member_id
                order by transacted_at
            ) is not null
            then {{ dbt.datediff(
                "lag(transacted_at) over (partition by loyalty_member_id order by transacted_at)",
                "transacted_at",
                "day"
            ) }}
            else null
        end as days_between_txns
    from loyalty_txns

),

final as (

    select
        loyalty_member_id,
        count(*) as total_transactions,
        avg(days_between_txns) as avg_days_between_transactions,
        min(days_between_txns) as min_days_between_transactions,
        max(days_between_txns) as max_days_between_transactions,
        min(transacted_at) as first_transaction_date,
        max(transacted_at) as last_transaction_date,
        case
            when avg(days_between_txns) is null then 'single_transaction'
            when avg(days_between_txns) <= 7 then 'weekly_active'
            when avg(days_between_txns) <= 30 then 'monthly_active'
            when avg(days_between_txns) <= 90 then 'quarterly_active'
            else 'infrequent'
        end as engagement_tier
    from member_txn_gaps
    group by 1

)

select * from final
