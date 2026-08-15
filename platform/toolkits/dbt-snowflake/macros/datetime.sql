{#
  Date and time functions.

  These mostly delegate to dbt-core's own cross-database macros rather than
  reimplementing them. dbt already maintains a correct implementation per adapter
  and will keep maintaining it; a second one here would be a second thing to keep
  right, and it would drift.

  What this file *does* own is the argument order. dbt and Snowflake disagree
  about `datediff`, and that disagreement is the single most dangerous thing in
  this toolkit — reversed arguments compile cleanly, run without error, and
  return a sign-flipped number. Every delegation below is written out explicitly
  so the mapping is visible in review rather than inferred.
#}


{#
  Snowflake: dateadd(part, value, date)
  dbt:       dbt.dateadd(datepart, interval, from_date_or_timestamp)
  Same order.
#}
{% macro sf_dateadd(datepart, value, expression) -%}
    {{ dbt.dateadd(datepart, value, expression) }}
{%- endmacro %}


{#
  Snowflake: datediff(part, start, end)          -- part first
  dbt:       dbt.datediff(first_date, second_date, datepart)  -- part last

  REVERSED. Passing Snowflake's arguments straight through to dbt's macro
  computes the difference between a date part and a date, which is either an
  error or nonsense depending on the adapter. The remap below is the reason this
  macro exists at all.
#}
{% macro sf_datediff(datepart, start_date, end_date) -%}
    {{ dbt.datediff(start_date, end_date, datepart) }}
{%- endmacro %}


{#
  Snowflake: date_trunc(part, date)
  dbt:       dbt.date_trunc(datepart, date)
  Same order. Note BigQuery's *native* date_trunc is (date, part) — delegating to
  dbt is what keeps that from mattering.
#}
{% macro sf_date_trunc(datepart, expression) -%}
    {{ dbt.date_trunc(datepart, expression) }}
{%- endmacro %}


{#
  Snowflake: last_day(date [, part])
  dbt:       dbt.last_day(date, datepart)
  Same order. Snowflake's part defaults to month; dbt's does not, so it is
  defaulted here rather than left to the caller to remember.
#}
{% macro sf_last_day(expression, datepart='month') -%}
    {{ dbt.last_day(expression, datepart) }}
{%- endmacro %}


{% macro sf_getdate() -%}
    {{ dbt.current_timestamp() }}
{%- endmacro %}


{% macro sf_sysdate() -%}
    {{ dbt.current_timestamp() }}
{%- endmacro %}


{#
  `dayofweek` numbering is a genuine semantic split rather than a syntax one:
  Snowflake counts Sunday as 0, Postgres and DuckDB agree with that via `dow`,
  and ISO numbering counts Monday as 1. Dispatching keeps the Snowflake answer
  on every adapter.
#}
{% macro sf_dayofweek(expression) -%}
    {{ return(adapter.dispatch('sf_dayofweek')(expression)) }}
{%- endmacro %}

{% macro default__sf_dayofweek(expression) -%}
    extract(dow from {{ expression }})
{%- endmacro %}

{% macro snowflake__sf_dayofweek(expression) -%}
    dayofweek({{ expression }})
{%- endmacro %}

{% macro bigquery__sf_dayofweek(expression) -%}
    {#- BigQuery's DAYOFWEEK is 1-7 with Sunday=1; shift to Sunday=0. -#}
    (extract(dayofweek from {{ expression }}) - 1)
{%- endmacro %}

{% macro clickhouse__sf_dayofweek(expression) -%}
    {#- ClickHouse toDayOfWeek is 1-7 with Monday=1; shift to Sunday=0. -#}
    (toDayOfWeek({{ expression }}) % 7)
{%- endmacro %}


{% macro sf_to_date(expression) -%}
    {{ return(adapter.dispatch('sf_to_date')(expression)) }}
{%- endmacro %}

{% macro default__sf_to_date(expression) -%}
    cast({{ expression }} as date)
{%- endmacro %}

{% macro clickhouse__sf_to_date(expression) -%}
    toDate({{ expression }})
{%- endmacro %}
