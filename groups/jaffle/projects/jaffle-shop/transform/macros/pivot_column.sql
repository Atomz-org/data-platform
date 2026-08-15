{#
    pivot_column(column, values, agg='sum', agg_column=none)

    Generates pivot expressions that turn row values into columns using
    conditional aggregation.

    Args:
        column: The column whose values will become new columns.
        values: A list of values to pivot on.
        agg: The aggregate function to use (default: 'sum'). Common: 'sum', 'count', 'avg', 'max', 'min'.
        agg_column: The column to aggregate. If none, uses 1 (useful for count).

    Usage:
        {{ pivot_column('status', ['placed', 'shipped', 'completed'], 'count') }}
        {{ pivot_column('category', ['food', 'drink'], 'sum', 'amount') }}

    Output (count example):
        count(case when status = 'placed' then 1 end) as placed_count,
        count(case when status = 'shipped' then 1 end) as shipped_count,
        count(case when status = 'completed' then 1 end) as completed_count
#}

{% macro pivot_column(column, values, agg='sum', agg_column=none) -%}
    {% for val in values -%}
        {% if agg_column is none -%}
            {{ agg }}(case when {{ column }} = '{{ val }}' then 1 end) as {{ val }}_{{ agg }}
        {%- else -%}
            {{ agg }}(case when {{ column }} = '{{ val }}' then {{ agg_column }} end) as {{ val }}_{{ agg }}
        {%- endif -%}
        {%- if not loop.last %},
    {% endif -%}
    {%- endfor -%}
{%- endmacro %}
