{% snapshot snp_dim_menu_items %}

{{
    config(
        target_schema='snapshots',
        unique_key='menu_item_id',
        strategy='check',
        check_cols=['menu_item_name', 'menu_item_price', 'is_available']
    )
}}

select * from {{ ref('dim_menu_items') }}

{% endsnapshot %}
