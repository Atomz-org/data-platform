-- adv_category_hierarchy.sql
-- Technique: Recursive CTE

{% set menu_categories_query %}
select * from {{ ref('dim_menu_categories') }}
{% endset %}

with recursive category_tree as (

    -- Anchor: root-level categories with no parent
    select
        menu_category_id as category_id,
        category_name,
        parent_category_id,
        parent_category_name as parent_category,
        0 as depth,
        category_name as full_path
    from ({{ menu_categories_query }}) as mc_anchor
    where parent_category_id is null

    union all

    -- Recursive step: children of already-discovered categories
    select
        child.menu_category_id as category_id,
        child.category_name,
        child.parent_category_id,
        parent.category_name as parent_category,
        parent.depth + 1 as depth,
        parent.full_path || ' > ' || child.category_name as full_path
    from ({{ menu_categories_query }}) as child
    inner join category_tree as parent
        on child.parent_category_id = parent.category_id

)

select
    category_id,
    category_name,
    parent_category,
    depth,
    full_path
from category_tree
order by full_path
