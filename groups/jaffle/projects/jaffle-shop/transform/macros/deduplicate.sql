{#
    deduplicate(relation, partition_by, order_by)

    Returns a deduplication query using row_number() that keeps only the first
    row per partition (ordered descending, so the most recent row wins).

    Args:
        relation: The source relation or CTE name to deduplicate.
        partition_by: Column(s) that define duplicate groups (e.g., 'customer_id').
        order_by: Column(s) to order by descending to pick the winner (e.g., 'updated_at').

    Usage:
        {{ deduplicate(ref('raw_orders'), 'order_id', 'updated_at') }}
        {{ deduplicate('source', 'customer_id, email', 'created_at') }}

    Output:
        (select *, row_number() over (partition by order_id order by updated_at desc) as _rn
        from raw_orders)
        where _rn = 1
#}

{% macro deduplicate(relation, partition_by, order_by) -%}
    select * from (
        select
            *,
            row_number() over (
                partition by {{ partition_by }}
                order by {{ order_by }} desc
            ) as _rn
        from {{ relation }}
    ) as _deduped
    where _rn = 1
{%- endmacro %}
