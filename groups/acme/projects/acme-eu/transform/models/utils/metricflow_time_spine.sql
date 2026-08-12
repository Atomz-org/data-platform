-- Required by MetricFlow for time-based metrics (offset windows, cumulative).
-- Platform-standard: daily grain, 2020-2030.
{{ config(materialized='table') }}
select cast(range as date) as date_day
from range(date '2020-01-01', date '2030-01-01', interval 1 day)
