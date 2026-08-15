{#
    safe_divide(numerator, denominator, default=0)

    Returns a division expression that handles division by zero and null denominators.

    Args:
        numerator: The numerator expression.
        denominator: The denominator expression.
        default: Value to return when denominator is zero or null (default: 0).

    Usage:
        {{ safe_divide('total_revenue', 'total_orders') }}
        {{ safe_divide('completed_tasks', 'total_tasks', default='null') }}

    Output:
        case when total_orders = 0 or total_orders is null then 0 else total_revenue::numeric / total_orders end
#}

{% macro safe_divide(numerator, denominator, default=0) -%}
    case
        when {{ denominator }} = 0 or {{ denominator }} is null then {{ default }}
        else {{ numerator }}::numeric / {{ denominator }}
    end
{%- endmacro %}
