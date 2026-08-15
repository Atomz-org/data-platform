{#
    running_total(column, partition_by=none, order_by='date_day')

    Returns a cumulative sum (running total) window expression.

    Args:
        column: The column to sum cumulatively.
        partition_by: Optional column(s) to partition by.
        order_by: Column to order by (default: 'date_day').

    Usage:
        {{ running_total('revenue', partition_by='store_id', order_by='date_day') }}
        {{ running_total('quantity') }}

    Output:
        sum(revenue) over (partition by store_id order by date_day rows between unbounded preceding and current row)
#}

{% macro running_total(column, partition_by=none, order_by='date_day') -%}
    sum({{ column }}) over (
        {% if partition_by is not none -%}
            partition by {{ partition_by }}
        {% endif -%}
        order by {{ order_by }} rows between unbounded preceding and current row
    )
{%- endmacro %}
