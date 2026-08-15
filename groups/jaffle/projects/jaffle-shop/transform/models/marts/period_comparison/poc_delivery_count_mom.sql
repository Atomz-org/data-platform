with

monthly_deliveries as (
    select
        {{ sf_date_trunc('month', "actual_arrival_at") }} as delivery_month,
        count(*) as delivery_count,
        avg(actual_transit_days) as avg_lead_time,
        count(case when is_on_time then 1 end) as on_time_count
    from {{ ref('fct_deliveries') }}
    group by 1
),

compared as (
    select
        delivery_month,
        delivery_count as current_deliveries,
        lag(delivery_count) over (order by delivery_month) as prior_month_deliveries,
        avg_lead_time as current_lead_time,
        lag(avg_lead_time) over (order by delivery_month) as prior_month_lead_time,
        round(on_time_count * 100.0 / nullif(delivery_count, 0), 2) as on_time_pct,
        round(((delivery_count - lag(delivery_count) over (order by delivery_month))) * 100.0
            / nullif(lag(delivery_count) over (order by delivery_month), 0), 2) as deliveries_mom_pct
    from monthly_deliveries
)

select * from compared
