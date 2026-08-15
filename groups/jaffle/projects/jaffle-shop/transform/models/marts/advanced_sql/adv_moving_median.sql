-- adv_moving_median.sql
-- Technique: Window Frame — Moving median via self-join + percentile_cont
-- Standard window functions don't support percentile_cont as a window aggregate,
-- so we use a self-join to compute the 7-day moving median per store.

with daily_store as (

    select * from {{ ref('int_daily_orders_by_store') }}

),

-- Use self-join to compute the 7-day moving median for each store-day
moving_median as (

    select
        ds.order_date,
        ds.location_id,
        ds.location_name,
        ds.total_revenue as daily_revenue,
        ds.order_count,
        med.median_revenue_7d,
        ds.total_revenue - med.median_revenue_7d as revenue_vs_median

    from daily_store as ds
    inner join (
        -- Compute the median of revenue over the 7-day window ending on each day
        select
            ds1.location_id,
            ds1.order_date,
            percentile_cont(0.5) within group (order by ds2.total_revenue) as median_revenue_7d
        from daily_store as ds1
        inner join daily_store as ds2
            on ds2.location_id = ds1.location_id
           and ds2.order_date between ds1.order_date - interval '6 days' and ds1.order_date
        group by ds1.location_id, ds1.order_date
    ) as med
        on ds.location_id = med.location_id
       and ds.order_date = med.order_date

)

select
    order_date,
    location_id,
    location_name,
    daily_revenue,
    order_count,
    round(median_revenue_7d, 2) as median_revenue_7d,
    round(revenue_vs_median, 2) as revenue_vs_median,
    case
        when median_revenue_7d > 0
        then round(daily_revenue / median_revenue_7d - 1 * 100, 1)
        else null
    end as pct_above_median
from moving_median
order by location_id, order_date
