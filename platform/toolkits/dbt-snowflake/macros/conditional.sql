{#
  Snowflake's conditional and null-handling functions, as portable dbt macros.

  Every macro here compiles to whatever the *target* adapter understands, so one
  model runs on DuckDB in development and Snowflake in production without being
  rewritten for either. The `sf_` prefix says where the semantics come from: the
  contract is "behaves the way Snowflake does", including where that differs from
  the local warehouse.

  Dispatch is used only where implementations genuinely differ. Most of these
  compile to ANSI SQL that every adapter already agrees on, and wrapping those in
  a dispatch would add indirection without adding portability.
#}


{% macro sf_iff(condition, true_result, false_result) -%}
    {{ return(adapter.dispatch('sf_iff')(condition, true_result, false_result)) }}
{%- endmacro %}

{% macro default__sf_iff(condition, true_result, false_result) -%}
    case when {{ condition }} then {{ true_result }} else {{ false_result }} end
{%- endmacro %}

{% macro snowflake__sf_iff(condition, true_result, false_result) -%}
    iff({{ condition }}, {{ true_result }}, {{ false_result }})
{%- endmacro %}

{% macro clickhouse__sf_iff(condition, true_result, false_result) -%}
    if({{ condition }}, {{ true_result }}, {{ false_result }})
{%- endmacro %}


{% macro sf_nvl(expression, replacement) -%}
    coalesce({{ expression }}, {{ replacement }})
{%- endmacro %}


{% macro sf_nvl2(expression, when_not_null, when_null) -%}
    case when {{ expression }} is not null then {{ when_not_null }} else {{ when_null }} end
{%- endmacro %}


{% macro sf_ifnull(expression, replacement) -%}
    coalesce({{ expression }}, {{ replacement }})
{%- endmacro %}


{% macro sf_zeroifnull(expression) -%}
    coalesce({{ expression }}, 0)
{%- endmacro %}


{% macro sf_nullifzero(expression) -%}
    nullif({{ expression }}, 0)
{%- endmacro %}


{#
  `least` and `greatest` are the quiet ones. Snowflake returns NULL if *any*
  argument is NULL; DuckDB, Postgres and BigQuery skip NULLs and return the
  smallest of the rest. Both behaviours are defensible and they disagree only on
  sparse rows, so the difference reaches a dashboard before it reaches a test.

  These reproduce Snowflake's rule explicitly on every adapter rather than
  inheriting whichever one the target happens to have.
#}
{% macro sf_least(expressions) -%}
    {{ _sf_null_propagating('least', expressions) }}
{%- endmacro %}


{% macro sf_greatest(expressions) -%}
    {{ _sf_null_propagating('greatest', expressions) }}
{%- endmacro %}


{% macro _sf_null_propagating(fn, expressions) -%}
    {%- if expressions is string -%}
        {%- set expressions = [expressions] -%}
    {%- endif -%}
    case
        when {{ expressions | join(' is null or ') }} is null then null
        else {{ fn }}({{ expressions | join(', ') }})
    end
{%- endmacro %}


{#
  Snowflake's `least_ignore_nulls` / `greatest_ignore_nulls` are the other half of
  the pair, and they match what most warehouses do natively.
#}
{% macro sf_least_ignore_nulls(expressions) -%}
    least({{ expressions | join(', ') if expressions is not string else expressions }})
{%- endmacro %}


{% macro sf_greatest_ignore_nulls(expressions) -%}
    greatest({{ expressions | join(', ') if expressions is not string else expressions }})
{%- endmacro %}
