-- adv_missing_data_detector.sql
-- Technique: Set difference via CROSS JOIN + LEFT JOIN anti-pattern
-- Cross joins the date spine with all store locations to generate every possible
-- store x date combination, then LEFT JOINs against actual orders to find
-- combinations with no data. This is a data quality pattern for detecting gaps
-- in coverage — missing store-days may indicate system outages, store closures,
-- or ETL failures.

with date_spine as (

    select date_day
    from {{ ref('util_date_spine') }}

),

locations as (

    select
        location_id,
        location_name
    from {{ ref('stg_locations') }}

),

-- Get the active period for each store (first order to last order)
store_active_range as (

    select
        location_id,
        min(ordered_at) as first_order_date,
        max(ordered_at) as last_order_date
    from {{ ref('stg_orders') }}
    group by 1

),

-- Cross join: generate every store x date within each store's active period
expected_combinations as (

    select
        l.location_id,
        l.location_name,
        ds.date_day
    from locations as l
    inner join store_active_range as sar
        on l.location_id = sar.location_id
    cross join date_spine as ds
    where ds.date_day between sar.first_order_date and sar.last_order_date

),

-- Actual orders per store per day
actual_orders as (

    select
        location_id,
        ordered_at as order_date,
        count(*) as order_count
    from {{ ref('stg_orders') }}
    group by 1, 2

),

-- Left join to find missing combinations
missing_data as (

    select
        ec.location_id,
        ec.location_name,
        ec.date_day,
        ao.order_count,

        -- Flag missing data
        case
            when ao.order_count is null then true
            else false
        end as is_missing,

        -- Days since last order for this store (to gauge severity)
        lag(case when ao.order_count is not null then ec.date_day end) over (
            partition by ec.location_id
            order by ec.date_day
        ) as last_order_date,

        -- Days until next order for this store
        lead(case when ao.order_count is not null then ec.date_day end) over (
            partition by ec.location_id
            order by ec.date_day
        ) as next_order_date

    from expected_combinations as ec
    left join actual_orders as ao
        on ec.location_id = ao.location_id
        and ec.date_day = ao.order_date

),

-- Only keep missing rows and enrich with gap context
final as (

    select
        location_id,
        location_name,
        date_day as missing_date,
        last_order_date,
        next_order_date,
        case
            when last_order_date is not null
            then (date_day - last_order_date)
            else null
        end as days_since_last_order,
        case
            when next_order_date is not null
            then (next_order_date - date_day)
            else null
        end as days_until_next_order,

        -- Severity classification
        case
            when (date_day - last_order_date) > 7 then 'critical'
            when (date_day - last_order_date) > 3 then 'warning'
            else 'info'
        end as severity

    from missing_data
    where is_missing = true

)

select * from final
order by location_id, missing_date
