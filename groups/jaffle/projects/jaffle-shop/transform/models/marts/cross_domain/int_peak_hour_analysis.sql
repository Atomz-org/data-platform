with hourly_data as (
    select
        store_id,
        order_hour,
        avg_orders_per_hour,
        avg_revenue_per_hour,
        total_orders_in_hour,
        hour_share_of_total_pct,
        store_total_orders
    from {{ ref('int_order_throughput_by_hour') }}
),

store_daily_avg as (
    select
        store_id,
        avg(avg_orders_per_hour) as overall_avg_orders_per_hour,
        stddev(avg_orders_per_hour) as stddev_orders_per_hour
    from hourly_data
    group by store_id
),

classified as (
    select
        hd.store_id,
        hd.order_hour,
        hd.avg_orders_per_hour,
        hd.avg_revenue_per_hour,
        hd.hour_share_of_total_pct,
        sda.overall_avg_orders_per_hour,
        sda.stddev_orders_per_hour,
        case
            when hd.avg_orders_per_hour > sda.overall_avg_orders_per_hour + sda.stddev_orders_per_hour
                then 'peak'
            when hd.avg_orders_per_hour < sda.overall_avg_orders_per_hour - sda.stddev_orders_per_hour
                then 'off_peak'
            else 'standard'
        end as hour_classification,
        rank() over (
            partition by hd.store_id
            order by hd.avg_orders_per_hour desc
        ) as hour_rank_by_volume
    from hourly_data as hd
    inner join store_daily_avg as sda
        on hd.store_id = sda.store_id
),

peak_summary as (
    select
        store_id,
        sum(case when hour_classification = 'peak' then hour_share_of_total_pct else 0 end) as peak_hours_share_pct,
        count(case when hour_classification = 'peak' then 1 end) as num_peak_hours,
        sum(case when hour_classification = 'peak' then avg_revenue_per_hour else 0 end) as peak_hours_avg_revenue
    from classified
    group by store_id
)

select
    c.store_id,
    c.order_hour,
    c.avg_orders_per_hour,
    c.avg_revenue_per_hour,
    c.hour_share_of_total_pct,
    c.hour_classification,
    c.hour_rank_by_volume,
    round(cast(c.overall_avg_orders_per_hour as {{ dbt.type_float() }}), 2) as store_avg_orders_per_hour,
    ps.num_peak_hours as store_total_peak_hours,
    round(cast(ps.peak_hours_share_pct as {{ dbt.type_float() }}), 2) as store_peak_hours_share_pct
from classified as c
inner join peak_summary as ps
    on c.store_id = ps.store_id
