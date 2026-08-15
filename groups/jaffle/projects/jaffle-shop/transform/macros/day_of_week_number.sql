{#
    Cross-database day of week extraction.
    Returns 0=Sunday, 1=Monday, ..., 6=Saturday (ISO-ish)
    
    Usage: {{ day_of_week_number('date_column') }}
#}

{% macro day_of_week_number(date_expr) %}
    {{ return(adapter.dispatch('day_of_week_number')(date_expr)) }}
{% endmacro %}

{% macro default__day_of_week_number(date_expr) %}
    extract(dow from {{ date_expr }})
{% endmacro %}

{% macro snowflake__day_of_week_number(date_expr) %}
    extract(dayofweek from {{ date_expr }})
{% endmacro %}

{% macro duckdb__day_of_week_number(date_expr) %}
    extract(dow from {{ date_expr }})
{% endmacro %}
