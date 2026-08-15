{{
    config(
        materialized='table'
    )
}}

-- Allocate total marketing spend equally across all stores
-- Flat query to avoid DuckDB nested CTE/subquery bug

select
    locations.location_id as store_id,
    locations.location_name as store_name,
    monthly_spend.spend_month,
    round(cast(monthly_spend.total_monthly_spend as {{ dbt.type_float() }}) / locations.num_stores, 2) as monthly_marketing_spend,
    monthly_spend.active_channels,
    monthly_spend.active_spend_days,
    round(
        cast(monthly_spend.total_monthly_spend as {{ dbt.type_float() }}) / locations.num_stores
        / nullif(monthly_spend.active_spend_days, 0), 2
    ) as avg_daily_marketing_spend,
    cast(null as varchar) as top_spend_channel,
    cast(null as {{ dbt.type_numeric() }}) as top_channel_spend

from (
    select location_id, location_name, count(*) over () as num_stores
    from {{ ref('stg_locations') }}
) locations

cross join (
    select
        {{ dbt.date_trunc("month", "spend_date") }} as spend_month,
        sum(channel_spend) as total_monthly_spend,
        count(distinct spend_channel) as active_channels,
        count(distinct spend_date) as active_spend_days
    from {{ ref('int_marketing_spend_daily') }}
    group by {{ dbt.date_trunc("month", "spend_date") }}
) monthly_spend
