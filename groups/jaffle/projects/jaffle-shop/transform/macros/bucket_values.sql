{#
    bucket_values(column, boundaries, labels)

    Generates a CASE WHEN chain that buckets a numeric column into labeled ranges.

    Args:
        column: The numeric column to bucket.
        boundaries: A list of boundary values (must be sorted ascending).
        labels: A list of labels for each bucket. Should have the same length as boundaries.
                The last label is used for values >= the last boundary.

    Usage:
        {{ bucket_values('amount', [0, 100, 500, 1000], ['small', 'medium', 'large', 'xlarge']) }}

    Output:
        case
            when amount < 100 then 'small'
            when amount < 500 then 'medium'
            when amount < 1000 then 'large'
            else 'xlarge'
        end
#}

{% macro bucket_values(column, boundaries, labels) -%}
    case
        {% for i in range(1, boundaries | length) -%}
            when {{ column }} < {{ boundaries[i] }} then '{{ labels[i - 1] }}'
        {% endfor -%}
        else '{{ labels[-1] }}'
    end
{%- endmacro %}
