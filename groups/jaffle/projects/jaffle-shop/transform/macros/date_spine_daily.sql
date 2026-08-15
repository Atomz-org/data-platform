{#
    date_spine_daily(start_date, end_date)

    Generates a daily date series using Postgres generate_series.
    Returns a CTE-ready query producing a single column 'date_day'.

    Args:
        start_date: The start date (inclusive), as a SQL expression or string literal.
        end_date: The end date (inclusive), as a SQL expression or string literal.

    Usage:
        {{ date_spine_daily("'2024-01-01'", "'2024-12-31'") }}
        {{ date_spine_daily("'2024-01-01'", "current_date") }}

    Output:
        select date_day::date as date_day
        from generate_series(
            '2024-01-01'::date,
            '2024-12-31'::date,
            '1 day'::interval
        ) as date_day
#}

{% macro date_spine_daily(start_date, end_date) -%}
    select date_day::date as date_day
    from generate_series(
        {{ start_date }}::date,
        {{ end_date }}::date,
        '1 day'::interval
    ) as date_day
{%- endmacro %}
