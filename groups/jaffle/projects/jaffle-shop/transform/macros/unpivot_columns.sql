{#
    unpivot_columns(columns, value_name='metric_value', key_name='metric_name')

    Generates a UNION ALL query to unpivot (melt) multiple columns into rows.
    Each column becomes a row with a key (column name) and value.

    This macro wraps a source relation reference and should be used within a
    model that defines the source CTE.

    Args:
        columns: A list of column names to unpivot.
        value_name: Name for the value column (default: 'metric_value').
        key_name: Name for the key column (default: 'metric_name').

    Usage (in a model):
        with source as (
            select * from {{ ref('my_model') }}
        )

        {{ unpivot_columns(['revenue', 'cost', 'profit']) }}

    Output:
        select 'revenue' as metric_name, revenue as metric_value from source
        union all
        select 'cost' as metric_name, cost as metric_value from source
        union all
        select 'profit' as metric_name, profit as metric_value from source
#}

{% macro unpivot_columns(columns, value_name='metric_value', key_name='metric_name') -%}
    {% for col in columns -%}
        select '{{ col }}' as {{ key_name }}, {{ col }} as {{ value_name }} from source
        {%- if not loop.last %}
        union all
        {% endif -%}
    {%- endfor -%}
{%- endmacro %}
