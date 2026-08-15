{#
    period_over_period(column, date_column, partition_by=none, periods_back=1)

    Returns a lag() window expression to retrieve a previous period's value.

    Args:
        column: The column to retrieve the lagged value for.
        date_column: The date/period column to order by.
        partition_by: Optional column(s) to partition by.
        periods_back: Number of periods to look back (default: 1).

    Usage:
        {{ period_over_period('revenue', 'month', partition_by='store_id') }}
        {{ period_over_period('total_orders', 'date_day', periods_back=7) }}

    Output:
        lag(revenue, 1) over (partition by store_id order by month)
#}

{% macro period_over_period(column, date_column, partition_by=none, periods_back=1) -%}
    lag({{ column }}, {{ periods_back }}) over (
        {% if partition_by is not none -%}
            partition by {{ partition_by }}
        {% endif -%}
        order by {{ date_column }}
    )
{%- endmacro %}
