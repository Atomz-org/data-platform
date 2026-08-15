{#
    weighted_score(columns_and_weights)

    Returns a weighted sum expression from a list of (column, weight) tuples.

    Args:
        columns_and_weights: A list of [column, weight] pairs.

    Usage:
        {{ weighted_score([('quality_score', 0.3), ('delivery_score', 0.4), ('price_score', 0.3)]) }}

    Output:
        (quality_score * 0.3 + delivery_score * 0.4 + price_score * 0.3)
#}

{% macro weighted_score(columns_and_weights) -%}
    (
        {%- for item in columns_and_weights -%}
            {{ item[0] }} * {{ item[1] }}
            {%- if not loop.last %} + {% endif -%}
        {%- endfor -%}
    )
{%- endmacro %}
