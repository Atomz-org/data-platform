with

refunds as (

    select * from {{ ref('fct_refunds') }}

),

refund_timeline as (

    select
        refund_id,
        order_id,
        location_id,
        refund_reason,
        refund_status,
        refund_amount,
        requested_date,
        resolved_date,
        days_to_resolution,
        is_approved,
        is_full_refund,

        -- Timeline stages
        case when requested_date is not null then true else false end as stage_1_requested,
        case when resolved_date is not null then true else false end as stage_2_reviewed,
        case when refund_status = 'approved' then true else false end as stage_3_approved,
        case when refund_status = 'denied' then true else false end as stage_3_denied,
        case
            when refund_status = 'approved' and resolved_date is not null
            then true
            else false
        end as stage_4_processed
    from refunds

),

monthly_summary as (

    select
        {{ dbt.date_trunc('month', 'requested_date') }} as refund_month,
        count(distinct refund_id) as total_refund_requests,
        count(distinct case when stage_2_reviewed then refund_id end) as reviewed,
        count(distinct case when stage_3_approved then refund_id end) as approved,
        count(distinct case when stage_3_denied then refund_id end) as denied,
        count(distinct case when stage_4_processed then refund_id end) as processed,
        round(avg(days_to_resolution), 1) as avg_days_to_resolution,
        round(
            (count(distinct case when stage_3_approved then refund_id end) * 100.0
            / nullif(count(distinct refund_id), 0)), 2
        ) as approval_rate_pct,
        sum(case when is_approved then refund_amount else 0 end) as total_approved_amount,
        round(
            (count(distinct case when is_full_refund and is_approved then refund_id end) * 100.0
            / nullif(count(distinct case when is_approved then refund_id end), 0)), 2
        ) as full_refund_pct
    from refund_timeline
    group by 1

)

select * from monthly_summary
