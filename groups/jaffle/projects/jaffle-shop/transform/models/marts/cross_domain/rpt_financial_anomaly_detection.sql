with refunds_raw as (
    select * from {{ ref('fct_refunds') }}
),

store_monthly as (
    select
        location_id as store_id,
        report_month,
        total_revenue,
        net_margin_pct
    from {{ ref('rpt_store_profitability') }}
),

revenue_change as (
    select
        store_id,
        report_month,
        total_revenue,
        net_margin_pct,
        lag(total_revenue) over (partition by store_id order by report_month) as prev_month_revenue,
        case
            when lag(total_revenue) over (partition by store_id order by report_month) > 0
                then round(
                    (total_revenue - lag(total_revenue) over (partition by store_id order by report_month))
                    / lag(total_revenue) over (partition by store_id order by report_month) * 100, 2
                )
            else 0
        end as revenue_change_pct
    from store_monthly
),

refund_rates as (
    select
        r.location_id as store_id,
        {{ dbt.date_trunc("month", "r.requested_date") }} as refund_month,
        count(distinct r.refund_id) as refund_count,
        sum(r.refund_amount) as total_refund_amount
    from refunds_raw as r
    group by r.location_id, {{ dbt.date_trunc("month", "r.requested_date") }}
),

refund_with_revenue as (
    select
        rc.store_id,
        rc.report_month,
        rc.total_revenue,
        coalesce(rr.refund_count, 0) as refund_count,
        coalesce(rr.total_refund_amount, 0) as total_refund_amount,
        case
            when rc.total_revenue > 0
                then round(coalesce(rr.total_refund_amount, 0) / rc.total_revenue * 100, 2)
            else 0
        end as refund_rate_pct
    from revenue_change as rc
    left join refund_rates as rr
        on rc.store_id = rr.store_id
        and rc.report_month = rr.refund_month
),

fleet_refund_stats as (
    select
        report_month,
        avg(refund_rate_pct) as fleet_avg_refund_rate,
        stddev(refund_rate_pct) as fleet_stddev_refund_rate
    from refund_with_revenue
    group by report_month
),

store_names as (
    select location_id as store_id, location_name as store_name
    from {{ ref('stg_locations') }}
),

anomalies as (
    select
        rc.store_id,
        rc.report_month,
        rc.total_revenue,
        rc.prev_month_revenue,
        rc.revenue_change_pct,
        rc.net_margin_pct,
        rwr.refund_count,
        rwr.total_refund_amount,
        rwr.refund_rate_pct,
        frs.fleet_avg_refund_rate,
        frs.fleet_stddev_refund_rate,

        -- Anomaly flags
        case when rc.revenue_change_pct <= -20 then true else false end as is_revenue_drop_anomaly,
        case
            when frs.fleet_stddev_refund_rate > 0
                and rwr.refund_rate_pct > frs.fleet_avg_refund_rate + 2 * frs.fleet_stddev_refund_rate
                then true
            else false
        end as is_refund_rate_anomaly,
        case when rc.net_margin_pct < -5 then true else false end as is_negative_margin_anomaly
    from revenue_change as rc
    left join refund_with_revenue as rwr
        on rc.store_id = rwr.store_id and rc.report_month = rwr.report_month
    left join fleet_refund_stats as frs
        on rc.report_month = frs.report_month
)

select
    sn.store_name,
    a.store_id,
    a.report_month,
    a.total_revenue,
    a.revenue_change_pct,
    a.net_margin_pct,
    a.refund_count,
    a.refund_rate_pct,
    round(cast(a.fleet_avg_refund_rate as {{ dbt.type_float() }}), 2) as fleet_avg_refund_rate,
    a.is_revenue_drop_anomaly,
    a.is_refund_rate_anomaly,
    a.is_negative_margin_anomaly,
    case
        when a.is_revenue_drop_anomaly and a.is_refund_rate_anomaly then 'critical'
        when a.is_revenue_drop_anomaly or a.is_negative_margin_anomaly then 'high'
        when a.is_refund_rate_anomaly then 'medium'
        else 'normal'
    end as anomaly_severity,
    (case when a.is_revenue_drop_anomaly then 1 else 0 end
        + case when a.is_refund_rate_anomaly then 1 else 0 end
        + case when a.is_negative_margin_anomaly then 1 else 0 end
    ) as anomaly_count
from anomalies as a
left join store_names as sn on a.store_id = sn.store_id
where a.is_revenue_drop_anomaly
    or a.is_refund_rate_anomaly
    or a.is_negative_margin_anomaly
