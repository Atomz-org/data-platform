-- adv_excluding_current_avg.sql
-- Technique: Window frame with ROWS BETWEEN ... AND 1 PRECEDING (excluding current row)
-- For each store-day, computes the average revenue of the 6 preceding days
-- (excluding the current day) using `rows between 6 preceding and 1 preceding`.
-- This creates a true "peer average" that isn't contaminated by the current day's
-- value, useful for anomaly detection and performance benchmarking.

with store_daily_revenue as (

    select * from {{ ref('int_revenue_by_store_daily') }}

),

-- Compute the excluding-current-row average and compare
with_peer_avg as (

    select
        revenue_date,
        location_id,
        location_name,
        total_revenue,
        invoice_count,

        -- Average of the 6 PRECEDING days, excluding today
        -- This is the key technique: rows between 6 preceding and 1 preceding
        avg(total_revenue) over (
            partition by location_id
            order by revenue_date
            rows between 6 preceding and 1 preceding
        ) as peer_avg_revenue_6d,

        -- Count of days in the window (to know if we have a full 6-day lookback)
        count(total_revenue) over (
            partition by location_id
            order by revenue_date
            rows between 6 preceding and 1 preceding
        ) as peer_days_count,

        -- For comparison: the standard 7-day average INCLUDING today
        avg(total_revenue) over (
            partition by location_id
            order by revenue_date
            rows between 6 preceding and current row
        ) as inclusive_avg_revenue_7d

    from store_daily_revenue

),

final as (

    select
        revenue_date,
        location_id,
        location_name,
        total_revenue,
        invoice_count,
        peer_days_count,

        round(peer_avg_revenue_6d, 2) as peer_avg_revenue_6d,
        round(inclusive_avg_revenue_7d, 2) as inclusive_avg_revenue_7d,

        -- Deviation from peer average
        round(total_revenue - peer_avg_revenue_6d, 2) as deviation_from_peer_avg,

        -- Percentage deviation
        case
            when peer_avg_revenue_6d is not null and peer_avg_revenue_6d > 0
            then round(
                ((total_revenue - peer_avg_revenue_6d) / peer_avg_revenue_6d * 100), 1
            )
            else null
        end as pct_deviation_from_peer,

        -- Flag anomalies: days where revenue deviates more than 50% from peer avg
        case
            when peer_avg_revenue_6d is not null and peer_avg_revenue_6d > 0
                and abs(total_revenue - peer_avg_revenue_6d) / peer_avg_revenue_6d > 0.5
            then true
            else false
        end as is_anomaly,

        -- Direction of anomaly
        case
            when peer_avg_revenue_6d is null then 'insufficient_data'
            when total_revenue > peer_avg_revenue_6d * 1.5 then 'spike'
            when total_revenue < peer_avg_revenue_6d * 0.5 then 'drop'
            else 'normal'
        end as anomaly_type

    from with_peer_avg
    -- Only show rows where we have at least 3 days of lookback data
    where peer_days_count >= 3

)

select * from final
order by location_id, revenue_date
