{#
    rolling_average(column, window_size, partition_by=none, order_by='date_day')

    Returns a rolling average window expression over the specified number of rows.

    Args:
        column: The column to average.
        window_size: Number of preceding rows to include (e.g., 7 for a 7-day rolling average).
        partition_by: Optional column(s) to partition by.
        order_by: Column to order by (default: 'date_day').

    Usage:
        {{ rolling_average('revenue', 7, partition_by='store_id', order_by='date_day') }}

    Output:
        avg(revenue) over (partition by store_id order by date_day rows between 6 preceding and current row)
#}

{% macro rolling_average(column, window_size, partition_by=none, order_by='date_day') -%}
    avg({{ column }}) over (
        {% if partition_by is not none -%}
            partition by {{ partition_by }}
        {% endif -%}
        order by {{ order_by }} rows between {{ window_size - 1 }} preceding and current row
    )
{%- endmacro %}
