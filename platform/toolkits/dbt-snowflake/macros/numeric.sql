{#
  Division and numeric coercion.

  `div0` is the one people reach for most and the one most often reimplemented
  slightly wrong: `a / nullif(b, 0)` returns NULL on a zero divisor, whereas
  Snowflake's `div0` returns 0. They differ on exactly the rows anyone added the
  guard for, so the distinction is preserved here rather than smoothed over.
#}


{% macro sf_div0(dividend, divisor) -%}
    coalesce({{ dividend }} / nullif({{ divisor }}, 0), 0)
{%- endmacro %}


{#
  Snowflake's `div0null` also treats a NULL divisor as zero, returning 0 where
  `div0` would return NULL.
#}
{% macro sf_div0null(dividend, divisor) -%}
    coalesce({{ dividend }} / nullif(coalesce({{ divisor }}, 0), 0), 0)
{%- endmacro %}


{#
  BigQuery's spelling, kept here so SQL adopted from BigQuery has a home too.
  Unlike `div0` it returns NULL rather than 0, which is BigQuery's behaviour.
#}
{% macro sf_safe_divide(dividend, divisor) -%}
    {{ dividend }} / nullif({{ divisor }}, 0)
{%- endmacro %}


{% macro sf_to_number(expression, precision=38, scale=0) -%}
    {{ return(adapter.dispatch('sf_to_number')(expression, precision, scale)) }}
{%- endmacro %}

{% macro default__sf_to_number(expression, precision, scale) -%}
    cast({{ expression }} as numeric({{ precision }}, {{ scale }}))
{%- endmacro %}

{% macro bigquery__sf_to_number(expression, precision, scale) -%}
    cast({{ expression }} as numeric)
{%- endmacro %}

{% macro clickhouse__sf_to_number(expression, precision, scale) -%}
    toDecimal128({{ expression }}, {{ scale }})
{%- endmacro %}


{#
  `try_to_number` returns NULL instead of raising on a value that will not parse.
  Adapters disagree about whether a failed cast is an error or a NULL, so this
  dispatches rather than assuming.
#}
{% macro sf_try_to_number(expression, precision=38, scale=0) -%}
    {{ return(adapter.dispatch('sf_try_to_number')(expression, precision, scale)) }}
{%- endmacro %}

{% macro default__sf_try_to_number(expression, precision, scale) -%}
    try_cast({{ expression }} as numeric({{ precision }}, {{ scale }}))
{%- endmacro %}

{% macro postgres__sf_try_to_number(expression, precision, scale) -%}
    {#- Postgres has no try_cast; a regex guard is the portable equivalent. -#}
    case
        when {{ expression }}::text ~ '^-?[0-9]+(\.[0-9]+)?$'
        then cast({{ expression }} as numeric({{ precision }}, {{ scale }}))
    end
{%- endmacro %}

{% macro bigquery__sf_try_to_number(expression, precision, scale) -%}
    safe_cast({{ expression }} as numeric)
{%- endmacro %}

{% macro clickhouse__sf_try_to_number(expression, precision, scale) -%}
    toDecimal128OrNull(toString({{ expression }}), {{ scale }})
{%- endmacro %}
