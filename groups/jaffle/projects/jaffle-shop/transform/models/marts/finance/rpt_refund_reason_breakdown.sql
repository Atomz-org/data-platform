with

refunds as (

    select * from {{ ref('fct_refunds') }}

),

reason_summary as (

    select
        refund_reason,
        location_id,
        {{ dbt.date_trunc('month', 'requested_date') }} as report_month,
        count(refund_id) as refund_count,
        sum(refund_amount) as total_refund_amount,
        avg(refund_amount) as avg_refund_amount,
        count(case when is_approved then 1 end) as approved_count,
        count(case when is_full_refund then 1 end) as full_refund_count,
        avg(days_to_resolution) as avg_days_to_resolution

    from refunds
    group by 1, 2, 3

),

with_shares as (

    select
        refund_reason,
        location_id,
        report_month,
        refund_count,
        total_refund_amount,
        avg_refund_amount,
        approved_count,
        full_refund_count,
        avg_days_to_resolution,
        sum(refund_count) over (
            partition by location_id, report_month
        ) as location_month_refund_count,
        case
            when sum(refund_count) over (
                partition by location_id, report_month
            ) > 0
                then refund_count::float / sum(refund_count) over (
                    partition by location_id, report_month
                )
            else 0
        end as reason_share_pct,
        case
            when sum(total_refund_amount) over (
                partition by location_id, report_month
            ) > 0
                then total_refund_amount / sum(total_refund_amount) over (
                    partition by location_id, report_month
                )
            else 0
        end as reason_amount_share_pct

    from reason_summary

)

select * from with_shares
