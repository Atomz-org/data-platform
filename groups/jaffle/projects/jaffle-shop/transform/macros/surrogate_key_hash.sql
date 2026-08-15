{#
    surrogate_key_hash(columns)

    Returns an MD5 hash expression that creates a deterministic surrogate key
    from multiple columns. Uses pipe ('|') as a delimiter to avoid collisions.

    Null values are coalesced to empty strings so the hash is always computed.

    Args:
        columns: A list of column names to include in the hash.

    Usage:
        {{ surrogate_key_hash(['order_id', 'customer_id', 'order_date']) }}

    Output:
        md5(coalesce(cast(order_id as text), '') || '|' || coalesce(cast(customer_id as text), '') || '|' || coalesce(cast(order_date as text), ''))
#}

{% macro surrogate_key_hash(columns) -%}
    md5(
        {%- for col in columns -%}
            coalesce(cast({{ col }} as text), '')
            {%- if not loop.last %} || '|' || {% endif -%}
        {%- endfor -%}
    )
{%- endmacro %}
