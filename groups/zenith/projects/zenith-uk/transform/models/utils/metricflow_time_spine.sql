-- Required by MetricFlow for time-based metrics. Platform-standard daily grain.
--
-- dbt_utils.date_spine, not DuckDB's range() table function: this model builds
-- on every target the project has, and range() exists only on DuckDB — on a
-- Postgres prod it was the one scaffolded model that failed the build.
{{ config(materialized='table') }}
select cast(date_day as date) as date_day
from ({{ dbt_utils.date_spine(
    datepart="day",
    start_date="cast('2020-01-01' as date)",
    end_date="cast('2030-01-01' as date)") }}) as spine
