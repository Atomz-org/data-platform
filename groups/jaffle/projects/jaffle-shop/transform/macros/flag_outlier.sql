{#
    flag_outlier(column, partition_by=none, std_dev_threshold=2)

    Returns a boolean expression that flags values as outliers based on
    standard deviation from the mean within an optional partition.

    Args:
        column: The numeric column to evaluate.
        partition_by: Optional column(s) to partition by.
        std_dev_threshold: Number of standard deviations from the mean to
                           consider a value an outlier (default: 2).

    Usage:
        {{ flag_outlier('order_total', partition_by='customer_segment') }}
        {{ flag_outlier('response_time', std_dev_threshold=3) }}

    Output:
        abs(order_total - avg(order_total) over (partition by customer_segment))
            > 2 * stddev(order_total) over (partition by customer_segment)
#}

{% macro flag_outlier(column, partition_by=none, std_dev_threshold=2) -%}
    abs({{ column }} - avg({{ column }}) over (
        {% if partition_by is not none -%}
            partition by {{ partition_by }}
        {% endif -%}
    )) > {{ std_dev_threshold }} * stddev({{ column }}) over (
        {% if partition_by is not none -%}
            partition by {{ partition_by }}
        {% endif -%}
    )
{%- endmacro %}
