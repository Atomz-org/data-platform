with

refunds as (

    select
        refund_id,
        order_id,
        refund_amount,
        refund_reason,
        refund_status,
        requested_date,
        resolved_date,
        case
            when resolved_date is not null
            then {{ dbt.datediff('requested_date', 'resolved_date', 'day') }}
            else null
        end as turnaround_days
    from {{ ref('fct_refunds') }}

),

summary as (

    select
        {{ dbt.date_trunc('month', 'requested_date') }} as refund_month,
        refund_reason,
        count(*) as total_refunds,
        sum(case when resolved_date is not null then 1 else 0 end) as completed_refunds,
        avg(turnaround_days) as avg_turnaround_days,
        min(turnaround_days) as min_turnaround_days,
        max(turnaround_days) as max_turnaround_days,
        sum(case when turnaround_days <= 1 then 1 else 0 end) as within_1_day,
        sum(case when turnaround_days <= 3 then 1 else 0 end) as within_3_days,
        sum(case when turnaround_days <= 7 then 1 else 0 end) as within_7_days,
        sum(refund_amount) as total_refund_amount
    from refunds
    group by 1, 2

)

select
    refund_month,
    refund_reason,
    total_refunds,
    completed_refunds,
    avg_turnaround_days,
    min_turnaround_days,
    max_turnaround_days,
    case
        when completed_refunds > 0
        then cast(within_1_day as {{ dbt.type_float() }}) / completed_refunds * 100
        else 0
    end as pct_within_1_day,
    case
        when completed_refunds > 0
        then cast(within_3_days as {{ dbt.type_float() }}) / completed_refunds * 100
        else 0
    end as pct_within_3_days,
    case
        when completed_refunds > 0
        then cast(within_7_days as {{ dbt.type_float() }}) / completed_refunds * 100
        else 0
    end as pct_within_7_days,
    total_refund_amount
from summary
