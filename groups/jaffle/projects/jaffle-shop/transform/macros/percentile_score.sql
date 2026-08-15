{#
    percentile_score(column, partition_by=none, n_tiles=100)

    Returns an ntile() window expression to assign percentile scores to rows.

    Args:
        column: The column to compute percentiles over (used in ORDER BY).
        partition_by: Optional column(s) to partition by.
        n_tiles: Number of tiles/buckets (default: 100 for percentiles).

    Usage:
        {{ percentile_score('revenue', partition_by='region', n_tiles=100) }}
        {{ percentile_score('score', n_tiles=10) }}

    Output:
        ntile(100) over (partition by region order by revenue)
#}

{% macro percentile_score(column, partition_by=none, n_tiles=100) -%}
    ntile({{ n_tiles }}) over (
        {% if partition_by is not none -%}
            partition by {{ partition_by }}
        {% endif -%}
        order by {{ column }}
    )
{%- endmacro %}
