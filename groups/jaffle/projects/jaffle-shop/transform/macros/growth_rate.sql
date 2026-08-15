{#
    growth_rate(current_col, previous_col)

    Returns a percentage growth rate expression using safe_divide to handle
    division by zero.

    Args:
        current_col: The current period's value column.
        previous_col: The previous period's value column.

    Usage:
        {{ growth_rate('current_revenue', 'previous_revenue') }}

    Output:
        (safe_divide(current_revenue - previous_revenue, abs(previous_revenue))) * 100

    Note:
        Depends on the safe_divide macro.
#}

{% macro growth_rate(current_col, previous_col) -%}
    ({{ safe_divide(current_col ~ ' - ' ~ previous_col, 'abs(' ~ previous_col ~ ')') }}) * 100
{%- endmacro %}
