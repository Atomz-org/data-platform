{#
  The price–open-interest read every Indian derivatives desk uses, from one
  day's price change and open-interest change:

      price ↑  OI ↑   long_buildup     new longs are paying up
      price ↓  OI ↑   short_buildup    new shorts are pressing
      price ↑  OI ↓   short_covering   shorts are buying back
      price ↓  OI ↓   long_unwinding   longs are selling out

  A day with either change zero or missing is `neutral`/null rather than forced
  into a quadrant — a flat settlement says nothing about who is in control.
#}
{% macro mcx_oi_buildup(price_change, oi_change) %}
    case
        when {{ price_change }} is null or {{ oi_change }} is null then null
        when {{ price_change }} > 0 and {{ oi_change }} > 0 then 'long_buildup'
        when {{ price_change }} < 0 and {{ oi_change }} > 0 then 'short_buildup'
        when {{ price_change }} > 0 and {{ oi_change }} < 0 then 'short_covering'
        when {{ price_change }} < 0 and {{ oi_change }} < 0 then 'long_unwinding'
        else 'neutral'
    end
{% endmacro %}
