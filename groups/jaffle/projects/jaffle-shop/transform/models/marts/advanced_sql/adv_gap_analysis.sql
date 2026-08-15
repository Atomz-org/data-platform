-- adv_gap_analysis.sql
-- Technique: Window Frame Trick — Gap detection in time series
-- Cross joins date_spine with locations to create a complete grid, then identifies
-- days where a store had no orders (gaps). Useful for detecting outages or closures.

with date_spine as (

    select date_day
    from {{ ref('util_date_spine') }}

),

locations as (

    select location_id, location_name
    from {{ ref('stg_locations') }}

),

daily_orders as (

    select * from {{ ref('int_daily_orders_by_store') }}

),

-- Get the date range where each store has had any orders
store_date_range as (

    select
        location_id,
        min(order_date) as first_order_date,
        max(order_date) as last_order_date
    from daily_orders
    group by 1

),

-- Create the full grid of store x date, only within each store's active period
store_date_grid as (

    select
        l.location_id,
        l.location_name,
        ds.date_day
    from locations as l
    inner join store_date_range as sdr
        on l.location_id = sdr.location_id
    inner join date_spine as ds
        on ds.date_day between sdr.first_order_date and sdr.last_order_date

),

-- Left join to find missing days
with_orders as (

    select
        g.location_id,
        g.location_name,
        g.date_day,
        d.total_revenue,
        d.order_count,
        case when d.order_count is null or d.order_count = 0 then true else false end as is_gap

    from store_date_grid as g
    left join daily_orders as d
        on g.location_id = d.location_id
        and g.date_day = d.order_date

),

-- Islands & gaps: group consecutive gap days together
gap_groups as (

    select
        *,
        -- Subtract a row_number to create gap group IDs:
        -- consecutive gap days will share the same gap_group value
        date_day - (row_number() over (
            partition by location_id, is_gap
            order by date_day
        ))::int as gap_group
    from with_orders
    where is_gap = true

),

-- Summarize each gap period
gap_summary as (

    select
        location_id,
        min(date_day) as gap_start_date,
        max(date_day) as gap_end_date,
        count(*) as gap_days
    from gap_groups
    group by location_id, gap_group

),

-- Get the revenue on the day before each gap started
final as (

    select
        gs.location_id,
        wo.location_name,
        gs.gap_start_date,
        gs.gap_end_date,
        gs.gap_days,
        prev.total_revenue as previous_day_revenue
    from gap_summary as gs
    left join with_orders as wo
        on gs.location_id = wo.location_id
        and gs.gap_start_date = wo.date_day
    left join daily_orders as prev
        on gs.location_id = prev.location_id
        and prev.order_date = gs.gap_start_date - interval '1 day'

)

select * from final
order by location_id, gap_start_date
