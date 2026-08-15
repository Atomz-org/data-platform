with

date_spine as (

    select * from {{ ref('util_date_spine') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

-- One row per store per day, starting from each store's opening date
store_calendar as (

    select
        ds.date_day,
        ds.day_of_week,
        ds.day_name,
        ds.week_start,
        ds.month_start,
        ds.is_weekend,
        l.location_id,
        l.location_name,
        {{ sf_datediff('day', "l.opened_date", "ds.date_day") }} as days_since_opening

    from date_spine as ds

    cross join locations as l

    where ds.date_day >= l.opened_date

)

select * from store_calendar
