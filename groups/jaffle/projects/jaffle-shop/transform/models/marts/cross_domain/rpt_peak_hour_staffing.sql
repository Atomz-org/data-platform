with peak_data as (
    select
        store_id,
        order_hour,
        avg_orders_per_hour,
        avg_revenue_per_hour,
        hour_classification,
        hour_share_of_total_pct,
        store_avg_orders_per_hour
    from {{ ref('int_peak_hour_analysis') }}
),

current_staffing as (
    select
        location_id,
        avg(scheduled_staff_count) as avg_total_staff,
        avg(orders_per_staff) as current_staffing_ratio
    from {{ ref('int_store_staffing_ratio') }}
    group by location_id
),

-- Estimate target orders per staff member from best-performing hours
target_efficiency as (
    select
        store_id,
        avg(avg_orders_per_hour) as baseline_orders_per_hour
    from peak_data
    where hour_classification = 'standard'
    group by store_id
)

select
    pd.store_id,
    pd.order_hour,
    pd.hour_classification,
    pd.avg_orders_per_hour,
    pd.avg_revenue_per_hour,
    pd.hour_share_of_total_pct,
    round(cast(cs.avg_total_staff as {{ dbt.type_float() }}), 1) as current_avg_staff,
    round(cast(cs.current_staffing_ratio as {{ dbt.type_float() }}), 2) as current_staffing_ratio,

    -- Recommended staff: scale linearly from baseline
    case
        when te.baseline_orders_per_hour > 0 and cs.avg_total_staff > 0
            then round(
                (cs.avg_total_staff * (pd.avg_orders_per_hour / te.baseline_orders_per_hour)), 1
            )
        else cs.avg_total_staff
    end as recommended_staff,

    -- Staffing gap
    case
        when te.baseline_orders_per_hour > 0 and cs.avg_total_staff > 0
            then round(
                (cs.avg_total_staff * (pd.avg_orders_per_hour / te.baseline_orders_per_hour)
                - cs.avg_total_staff), 1
            )
        else 0
    end as staffing_gap,

    case
        when pd.hour_classification = 'peak'
            and te.baseline_orders_per_hour > 0
            and pd.avg_orders_per_hour / te.baseline_orders_per_hour > 1.3
            then 'understaffed_during_peak'
        when pd.hour_classification = 'off_peak'
            and cs.avg_total_staff > 2
            then 'potentially_overstaffed'
        else 'adequately_staffed'
    end as staffing_recommendation

from peak_data as pd
left join current_staffing as cs
    on pd.store_id = cs.location_id
left join target_efficiency as te
    on pd.store_id = te.store_id
