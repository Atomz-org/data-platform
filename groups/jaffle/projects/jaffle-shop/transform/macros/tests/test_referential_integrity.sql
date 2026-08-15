{% test referential_integrity(model, column_name, to_model, to_column) %}

select a.{{ column_name }}
from {{ model }} a
left join {{ to_model }} b on a.{{ column_name }} = b.{{ to_column }}
where b.{{ to_column }} is null and a.{{ column_name }} is not null

{% endtest %}
