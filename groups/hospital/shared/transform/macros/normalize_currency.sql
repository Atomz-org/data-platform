{% macro normalize_currency(amount_col, currency_col, target='USD') %}
    -- Applied automatically wherever a money_amount / currency_code pair is
    -- annotated. Rates come from the group's fx seed; contracts are struck at
    -- signature and never re-struck.
    case
        when {{ currency_col }} = '{{ target }}' then {{ amount_col }}
        else {{ amount_col }} * coalesce(fx.rate, 1.0)
    end
{% endmacro %}
