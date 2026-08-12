{#
  Role-driven cleaning macros. One per ontology column role.

  Staging applies these; nothing downstream re-cleans. Because the role is
  declared once on the dlt resource, every project cleans the same way and a new
  company inherits the rules without writing them.
#}

{% macro clean_text(col) %}
    nullif(trim({{ col }}), '')
{% endmacro %}


{% macro clean_natural_key(col) %}
    {#- keys are trimmed and blank-normalised; never lower-cased (they are opaque) -#}
    nullif(trim({{ col }}), '')
{% endmacro %}


{% macro clean_email(col) %}
    {#- emails are case-insensitive by RFC; lower so joins and dedupes work -#}
    nullif(lower(trim({{ col }})), '')
{% endmacro %}


{% macro clean_status(col) %}
    {#- enum values normalise to lower snake so accepted_values stays stable -#}
    nullif(lower(trim({{ col }})), '')
{% endmacro %}


{% macro clean_currency(col) %}
    {#- ISO 4217 is upper case; anything not 3 chars is bad data, not a currency -#}
    case
        when length(trim({{ col }})) = 3 then upper(trim({{ col }}))
        else null
    end
{% endmacro %}


{% macro clean_country(col) %}
    case
        when length(trim({{ col }})) = 2 then upper(trim({{ col }}))
        else null
    end
{% endmacro %}


{% macro clean_money(col, scale=2, minor_units=false) %}
    {#- sentinel negatives from source systems are nulls, not amounts -#}
    case
        when try_cast({{ col }} as decimal(18, {{ scale }})) is null then null
        else round(
            try_cast({{ col }} as decimal(18, {{ scale }}))
            {% if minor_units %} / 100.0 {% endif %}, {{ scale }})
    end
{% endmacro %}


{% macro clean_quantity(col) %}
    case when try_cast({{ col }} as bigint) < 0 then null
         else try_cast({{ col }} as bigint) end
{% endmacro %}


{% macro clean_timestamp(col) %}
    {#- source systems emit '', 'N/A' and 0001-01-01 for "no value" -#}
    case
        when try_cast({{ col }} as timestamp) is null then null
        when try_cast({{ col }} as timestamp) < timestamp '1970-01-01' then null
        else try_cast({{ col }} as timestamp)
    end
{% endmacro %}


{% macro clean_name(col) %}
    {#- collapse internal whitespace; keep case (names are not case-insensitive) -#}
    nullif(regexp_replace(trim({{ col }}), '\s+', ' ', 'g'), '')
{% endmacro %}


{% macro pf_clean(col, role) %}
    {#- Dispatch on ontology role. Unknown roles pass through untouched. -#}
    {%- if role == 'natural_key' or role == 'surrogate_key' or role == 'foreign_key' -%}
        {{ clean_natural_key(col) }}
    {%- elif role == 'pii_email' -%}          {{ clean_email(col) }}
    {%- elif role == 'pii_name' -%}           {{ clean_name(col) }}
    {%- elif role == 'pii_phone' -%}          {{ clean_text(col) }}
    {%- elif role == 'pii_address' -%}        {{ clean_name(col) }}
    {%- elif role == 'status_enum' -%}        {{ clean_status(col) }}
    {%- elif role == 'currency_code' -%}      {{ clean_currency(col) }}
    {%- elif role == 'geo_country' -%}        {{ clean_country(col) }}
    {%- elif role == 'money_amount' -%}       {{ clean_money(col) }}
    {%- elif role == 'quantity' -%}           {{ clean_quantity(col) }}
    {%- elif role in ('event_time', 'valid_from', 'valid_to') -%}
        {{ clean_timestamp(col) }}
    {%- elif role == 'free_text' -%}          {{ clean_text(col) }}
    {%- else -%}                              {{ col }}
    {%- endif -%}
{% endmacro %}


{% macro pf_dedupe(key_col, order_col='_dlt_load_id') %}
    {#- dlt merge can still land duplicates when a source replays. Staging is the
        last place to fix that at 1:1 grain. -#}
    qualify row_number() over (
        partition by {{ key_col }} order by {{ order_col }} desc
    ) = 1
{% endmacro %}
