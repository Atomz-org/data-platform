{#
  String functions.

  `charindex` and `listagg` delegate to dbt-core, which already has a per-adapter
  implementation. The rest dispatch, because the adapters genuinely disagree
  about spelling, argument order, or both.
#}


{#
  Snowflake: charindex(needle, haystack)
  dbt:       dbt.position(substring_text, string_text)
  Same order. Worth stating, because DuckDB's own `instr(haystack, needle)` is
  the other way round and a hand-written mapping usually gets it backwards.
#}
{% macro sf_charindex(needle, haystack) -%}
    {{ dbt.position(needle, haystack) }}
{%- endmacro %}


{% macro sf_split_part(expression, delimiter, part_number) -%}
    {{ dbt.split_part(expression, delimiter, part_number) }}
{%- endmacro %}


{#
  Snowflake: listagg(measure, delimiter) WITHIN GROUP (ORDER BY ...)
  dbt:       dbt.listagg(measure, delimiter_text, order_by_clause, limit_num)

  The ordering clause is a separate argument rather than trailing syntax. Passing
  none is legal and non-deterministic — which is fine for a set and wrong for
  anything a human will read, so it is worth passing explicitly.
#}
{% macro sf_listagg(measure, delimiter="','", order_by_clause=none, limit_num=none) -%}
    {{ dbt.listagg(measure, delimiter, order_by_clause, limit_num) }}
{%- endmacro %}


{% macro sf_regexp_substr(expression, pattern) -%}
    {{ return(adapter.dispatch('sf_regexp_substr')(expression, pattern)) }}
{%- endmacro %}

{% macro default__sf_regexp_substr(expression, pattern) -%}
    substring({{ expression }} from {{ pattern }})
{%- endmacro %}

{% macro duckdb__sf_regexp_substr(expression, pattern) -%}
    regexp_extract({{ expression }}, {{ pattern }})
{%- endmacro %}

{% macro snowflake__sf_regexp_substr(expression, pattern) -%}
    regexp_substr({{ expression }}, {{ pattern }})
{%- endmacro %}

{% macro bigquery__sf_regexp_substr(expression, pattern) -%}
    regexp_extract({{ expression }}, {{ pattern }})
{%- endmacro %}

{% macro clickhouse__sf_regexp_substr(expression, pattern) -%}
    extract({{ expression }}, {{ pattern }})
{%- endmacro %}


{% macro sf_to_varchar(expression) -%}
    {{ return(adapter.dispatch('sf_to_varchar')(expression)) }}
{%- endmacro %}

{% macro default__sf_to_varchar(expression) -%}
    cast({{ expression }} as varchar)
{%- endmacro %}

{% macro bigquery__sf_to_varchar(expression) -%}
    cast({{ expression }} as string)
{%- endmacro %}

{% macro clickhouse__sf_to_varchar(expression) -%}
    toString({{ expression }})
{%- endmacro %}


{#
  Snowflake's `regexp_like` is a boolean predicate, spelled differently almost
  everywhere and with genuinely different regex flavours underneath. The spelling
  is handled here; the flavour is not, and a pattern using backreferences or
  lookaround will still need a human.
#}
{% macro sf_regexp_like(expression, pattern) -%}
    {{ return(adapter.dispatch('sf_regexp_like')(expression, pattern)) }}
{%- endmacro %}

{% macro default__sf_regexp_like(expression, pattern) -%}
    {{ expression }} ~ {{ pattern }}
{%- endmacro %}

{% macro duckdb__sf_regexp_like(expression, pattern) -%}
    regexp_matches({{ expression }}, {{ pattern }})
{%- endmacro %}

{% macro snowflake__sf_regexp_like(expression, pattern) -%}
    regexp_like({{ expression }}, {{ pattern }})
{%- endmacro %}

{% macro bigquery__sf_regexp_like(expression, pattern) -%}
    regexp_contains({{ expression }}, {{ pattern }})
{%- endmacro %}

{% macro clickhouse__sf_regexp_like(expression, pattern) -%}
    match({{ expression }}, {{ pattern }})
{%- endmacro %}
