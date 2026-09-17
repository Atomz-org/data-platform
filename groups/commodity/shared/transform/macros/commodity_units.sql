{#
  Conformed price arithmetic for every commodity sister.

  Order matters and is always the same: minor currency → major currency, then
  quote unit → market unit, then FX. Each step is here exactly once.
#}

{% macro to_major_currency(price_col, currency_col) %}
    {#- Yahoo reports CBOT grains, ICE softs and CME livestock in US cents (USX).
        A cents quote read as dollars is a 100x error that no range test catches
        on its own, because 732.5 is a plausible number for many benchmarks. -#}
    case upper({{ currency_col }})
        when 'USX' then {{ price_col }} / 100.0
        when 'GBX' then {{ price_col }} / 100.0
        else {{ price_col }}
    end
{% endmacro %}


{% macro major_currency_code(currency_col) %}
    case upper({{ currency_col }})
        when 'USX' then 'USD'
        when 'GBX' then 'GBP'
        else upper({{ currency_col }})
    end
{% endmacro %}


{% macro reprice_per_unit(price_col, from_base_units_col, to_base_units_col) %}
    {#- Price per one `from` unit → price per one `to` unit. Both sizes come from
        the group's `units_of_measure` seed in the same base unit, so the ratio
        is the number of `to` units in one `from` unit, inverted. Example: $4310/troy oz
        × (0.001 kg / 0.0311034768 kg) = $138.57/g. Callers must join units of
        the same `dimension`; a singular test in each sister enforces that. -#}
    ({{ price_col }} * {{ to_base_units_col }} / nullif({{ from_base_units_col }}, 0))
{% endmacro %}
