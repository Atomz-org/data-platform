with throughput as (
    select
        store_id,
        sum(total_orders_in_hour) as total_orders,
        avg(avg_orders_per_hour) as avg_orders_per_hour,
        max(peak_orders_in_hour) as max_orders_in_hour
    from {{ ref('int_order_throughput_by_hour') }}
    group by store_id
),

peak_hours as (
    select
        store_id,
        store_total_peak_hours,
        store_peak_hours_share_pct,
        max(case when hour_rank_by_volume = 1 then order_hour end) as busiest_hour
    from {{ ref('int_peak_hour_analysis') }}
    group by store_id, store_total_peak_hours, store_peak_hours_share_pct
),

revenue_efficiency as (
    select
        location_id as store_id,
        round(cast(avg(revenue_per_labor_hour) as {{ dbt.type_float() }}), 2) as avg_revenue_per_labor_hour,
        round(cast(avg(revenue_per_employee) as {{ dbt.type_float() }}), 2) as avg_revenue_per_employee,
        sum(total_hours_worked) as total_labor_hours,
        sum(total_revenue) as total_revenue
    from {{ ref('int_revenue_per_employee_hour') }}
    group by location_id
),

staffing as (
    select
        location_id as store_id,
        avg(orders_per_staff) as avg_staffing_ratio
    from {{ ref('int_store_staffing_ratio') }}
    group by location_id
),

store_names as (
    select location_id as store_id, location_name as store_name
    from {{ ref('stg_locations') }}
),

fleet_benchmarks as (
    select
        avg(re.avg_revenue_per_labor_hour) as fleet_avg_rev_per_hour,
        avg(t.avg_orders_per_hour) as fleet_avg_orders_per_hour
    from revenue_efficiency as re
    inner join throughput as t on re.store_id = t.store_id
)

select
    sn.store_name,
    t.store_id,
    t.total_orders,
    round(cast(t.avg_orders_per_hour as {{ dbt.type_float() }}), 2) as avg_orders_per_hour,
    t.max_orders_in_hour,
    ph.store_total_peak_hours,
    ph.store_peak_hours_share_pct,
    ph.busiest_hour,
    re.avg_revenue_per_labor_hour,
    re.avg_revenue_per_employee,
    re.total_labor_hours,
    round(cast(st.avg_staffing_ratio as {{ dbt.type_float() }}), 2) as avg_staffing_ratio,

    -- Efficiency vs fleet
    round(cast(re.avg_revenue_per_labor_hour - fb.fleet_avg_rev_per_hour as {{ dbt.type_float() }}), 2) as rev_per_hour_vs_fleet,
    round(cast(t.avg_orders_per_hour - fb.fleet_avg_orders_per_hour as {{ dbt.type_float() }}), 2) as orders_per_hour_vs_fleet,

    -- Composite efficiency score (normalized 0-100)
    round(
        (percent_rank() over (order by re.avg_revenue_per_labor_hour) * 0.4
        + percent_rank() over (order by t.avg_orders_per_hour) * 0.3
        + percent_rank() over (order by re.avg_revenue_per_employee) * 0.3) * 100, 2
    ) as efficiency_score,

    rank() over (order by re.avg_revenue_per_labor_hour desc) as efficiency_rank

from throughput as t
left join peak_hours as ph on t.store_id = ph.store_id
left join revenue_efficiency as re on t.store_id = re.store_id
left join staffing as st on t.store_id = st.store_id
left join store_names as sn on t.store_id = sn.store_id
cross join fleet_benchmarks as fb
